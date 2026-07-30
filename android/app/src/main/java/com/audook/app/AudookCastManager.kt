package com.audook.app

import android.content.Context
import android.net.Uri
import androidx.mediarouter.media.MediaRouteSelector
import androidx.mediarouter.media.MediaRouter
import com.google.android.gms.cast.CastMediaControlIntent
import com.google.android.gms.cast.MediaInfo
import com.google.android.gms.cast.MediaLoadRequestData
import com.google.android.gms.cast.MediaMetadata
import com.google.android.gms.cast.MediaStatus
import com.google.android.gms.cast.framework.CastContext
import com.google.android.gms.cast.framework.CastSession
import com.google.android.gms.cast.framework.SessionManagerListener
import com.google.android.gms.cast.framework.media.RemoteMediaClient
import com.google.android.gms.common.images.WebImage

/**
 * Chromecast/Google Home casting via the real Cast Sender SDK - fully
 * independent of the NAS backend (unlike desktop, which drives casting
 * through its own PlayerService/pychromecast session). Device discovery
 * uses MediaRouter (the standard integration point the Cast SDK plugs into),
 * and playback goes through RemoteMediaClient once a session is active.
 *
 * Deliberately does not know about the book's chapter list itself -
 * AudookPlayerPlugin keeps driving "which chapter" the same way it already
 * does for local playback (the local ExoPlayer playlist stays loaded and
 * paused while casting, purely as a source of truth for chapter sequencing)
 * and just tells this class to mirror whichever chapter is now current to
 * the cast device instead of sounding it locally.
 */
class AudookCastManager(private val context: Context) {

    interface Listener {
        fun onDevicesChanged(devices: List<CastDeviceInfo>)
        fun onCastStateChanged(isCasting: Boolean, deviceName: String?)
        // The currently loaded chapter finished playing on the cast device -
        // mirrors the local STATE_ENDED signal so the plugin can advance to
        // the next chapter the same way it does locally.
        fun onRemoteChapterEnded()
        // Play/pause state changed on the cast device (either from our own
        // pause()/resume() calls or from someone using the TV/receiver's own
        // remote) - mirrors the local onIsPlayingChanged callback.
        fun onRemotePlayingChanged(isPlaying: Boolean)
    }

    data class CastDeviceInfo(val id: String, val name: String)

    var listener: Listener? = null

    private val mediaRouter = MediaRouter.getInstance(context)
    private val routeSelector = MediaRouteSelector.Builder()
        .addControlCategory(CastMediaControlIntent.categoryForCast(CastMediaControlIntent.DEFAULT_MEDIA_RECEIVER_APPLICATION_ID))
        .build()

    private var castContext: CastContext? = null
    private var currentSession: CastSession? = null
    private var remoteMediaClient: RemoteMediaClient? = null
    private var discovering = false

    private val routerCallback = object : MediaRouter.Callback() {
        override fun onRouteAdded(router: MediaRouter, route: MediaRouter.RouteInfo) = notifyDevices()
        override fun onRouteRemoved(router: MediaRouter, route: MediaRouter.RouteInfo) = notifyDevices()
        override fun onRouteChanged(router: MediaRouter, route: MediaRouter.RouteInfo) = notifyDevices()
    }

    private val sessionManagerListener = object : SessionManagerListener<CastSession> {
        override fun onSessionStarted(session: CastSession, sessionId: String) = attachSession(session)
        override fun onSessionResumed(session: CastSession, wasSuspended: Boolean) = attachSession(session)
        override fun onSessionEnded(session: CastSession, error: Int) = detachSession()
        override fun onSessionStartFailed(session: CastSession, error: Int) = detachSession()
        override fun onSessionEnding(session: CastSession) {}
        override fun onSessionResumeFailed(session: CastSession, error: Int) {}
        override fun onSessionResuming(session: CastSession, sessionId: String) {}
        override fun onSessionStarting(session: CastSession) {}
        override fun onSessionSuspended(session: CastSession, reason: Int) {}
    }

    private var lastKnownRemotePlaying: Boolean? = null

    private val remoteMediaClientCallback = object : RemoteMediaClient.Callback() {
        override fun onStatusUpdated() {
            val client = remoteMediaClient ?: return
            val status = client.mediaStatus ?: return
            if (status.idleReason == MediaStatus.IDLE_REASON_FINISHED) {
                listener?.onRemoteChapterEnded()
            }
            val playing = client.isPlaying
            if (playing != lastKnownRemotePlaying) {
                lastKnownRemotePlaying = playing
                listener?.onRemotePlayingChanged(playing)
            }
        }
    }

    private fun attachSession(session: CastSession) {
        currentSession = session
        remoteMediaClient = session.remoteMediaClient
        remoteMediaClient?.registerCallback(remoteMediaClientCallback)
        listener?.onCastStateChanged(true, session.castDevice?.friendlyName)
    }

    private fun detachSession() {
        remoteMediaClient?.unregisterCallback(remoteMediaClientCallback)
        currentSession = null
        remoteMediaClient = null
        listener?.onCastStateChanged(false, null)
    }

    private fun ensureCastContext(): CastContext? {
        if (castContext == null) {
            try {
                castContext = CastContext.getSharedInstance(context)
                castContext?.sessionManager?.addSessionManagerListener(sessionManagerListener, CastSession::class.java)
            } catch (e: Exception) {
                // Google Play Services unavailable/outdated on this device -
                // casting just silently stays unavailable rather than crash.
                castContext = null
            }
        }
        return castContext
    }

    fun startDiscovery() {
        if (discovering) return
        ensureCastContext() ?: return
        discovering = true
        mediaRouter.addCallback(routeSelector, routerCallback, MediaRouter.CALLBACK_FLAG_REQUEST_DISCOVERY)
        notifyDevices()
    }

    fun stopDiscovery() {
        if (!discovering) return
        discovering = false
        mediaRouter.removeCallback(routerCallback)
    }

    private fun notifyDevices() {
        val devices = mediaRouter.routes
            .filter { it.matchesSelector(routeSelector) && !it.isDefaultOrBluetooth }
            .map { CastDeviceInfo(it.id, it.name.toString()) }
        listener?.onDevicesChanged(devices)
    }

    fun connect(deviceId: String): Boolean {
        val route = mediaRouter.routes.find { it.id == deviceId } ?: return false
        mediaRouter.selectRoute(route)
        return true
    }

    fun disconnect() {
        castContext?.sessionManager?.endCurrentSession(true)
    }

    fun isCasting(): Boolean = currentSession != null

    fun castDeviceName(): String? = currentSession?.castDevice?.friendlyName

    fun loadMedia(url: String, title: String, cover: String?, positionMs: Long, autoplay: Boolean = true) {
        val client = remoteMediaClient ?: return
        val metadata = MediaMetadata(MediaMetadata.MEDIA_TYPE_MUSIC_TRACK)
        metadata.putString(MediaMetadata.KEY_TITLE, title)
        if (cover != null) {
            try {
                metadata.addImage(WebImage(Uri.parse(cover)))
            } catch (e: Exception) { /* bad/unparseable cover URL - just skip artwork */ }
        }
        val mediaInfo = MediaInfo.Builder(url)
            .setStreamType(MediaInfo.STREAM_TYPE_BUFFERED)
            .setContentType("audio/mpeg")
            .setMetadata(metadata)
            .build()
        val request = MediaLoadRequestData.Builder()
            .setMediaInfo(mediaInfo)
            .setAutoplay(autoplay)
            .setCurrentTime(positionMs)
            .build()
        client.load(request)
    }

    fun seek(ms: Long) {
        remoteMediaClient?.seek(ms)
    }

    fun pause() {
        remoteMediaClient?.pause()
    }

    fun resume() {
        remoteMediaClient?.play()
    }

    fun getPositionMs(): Long = remoteMediaClient?.approximateStreamPosition ?: 0L
    fun getDurationMs(): Long = remoteMediaClient?.mediaInfo?.streamDuration ?: 0L
    fun isPlaying(): Boolean = remoteMediaClient?.isPlaying == true
}
