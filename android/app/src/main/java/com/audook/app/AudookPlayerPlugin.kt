package com.audook.app

import android.content.ComponentName
import android.os.Handler
import android.os.Looper
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.google.common.util.concurrent.MoreExecutors

/**
 * JS-facing bridge to the background-audio playback service
 * (AudookPlaybackService). Talks to it through a MediaController so
 * playback survives screen-lock/backgrounding regardless of the WebView's
 * own lifecycle - see useMobilePlayerState.ts for the JS side.
 */
@CapacitorPlugin(name = "AudookPlayer")
class AudookPlayerPlugin : Plugin() {

    private var controller: MediaController? = null
    private val positionHandler = Handler(Looper.getMainLooper())
    private var positionRunnable: Runnable? = null

    override fun load() {
        val sessionToken = SessionToken(
            context,
            ComponentName(context, AudookPlaybackService::class.java)
        )
        val future = MediaController.Builder(context, sessionToken).buildAsync()
        future.addListener({
            controller = future.get()
            controller?.addListener(playerListener)
        }, MoreExecutors.directExecutor())
    }

    private val playerListener = object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) {
            if (isPlaying) startPositionUpdates() else stopPositionUpdates()
            val data = JSObject()
            data.put("isPlaying", isPlaying)
            notifyListeners("stateChange", data)
        }

        override fun onPlaybackStateChanged(playbackState: Int) {
            if (playbackState == Player.STATE_ENDED) {
                val data = JSObject()
                data.put("ended", true)
                notifyListeners("ended", data)
            }
        }
    }

    private fun startPositionUpdates() {
        stopPositionUpdates()
        val runnable = object : Runnable {
            override fun run() {
                emitPosition()
                positionHandler.postDelayed(this, 1000)
            }
        }
        positionRunnable = runnable
        positionHandler.post(runnable)
    }

    private fun stopPositionUpdates() {
        positionRunnable?.let { positionHandler.removeCallbacks(it) }
        positionRunnable = null
    }

    private fun emitPosition() {
        val c = controller ?: return
        val data = JSObject()
        data.put("positionMs", c.currentPosition)
        data.put("durationMs", if (c.duration > 0) c.duration else 0)
        notifyListeners("positionUpdate", data)
    }

    @PluginMethod
    fun play(call: PluginCall) {
        val url = call.getString("url")
        val title = call.getString("title") ?: ""
        val cover = call.getString("cover")

        if (url == null) {
            call.reject("url is required")
            return
        }

        val c = controller
        if (c == null) {
            call.reject("Player not ready")
            return
        }

        val metadataBuilder = MediaMetadata.Builder().setTitle(title)
        if (cover != null) {
            metadataBuilder.setArtworkUri(android.net.Uri.parse(cover))
        }

        val mediaItem = MediaItem.Builder()
            .setUri(url)
            .setMediaMetadata(metadataBuilder.build())
            .build()

        // MediaController must only be touched from the thread that built it
        // (the main thread here, via positionHandler) - Capacitor plugin
        // methods run on their own "CapacitorPlugins" handler thread, which
        // crashed the app with IllegalStateException before this dispatch.
        positionHandler.post {
            c.setMediaItem(mediaItem)
            c.prepare()
            c.play()
        }
        call.resolve()
    }

    @PluginMethod
    fun pause(call: PluginCall) {
        positionHandler.post { controller?.pause() }
        call.resolve()
    }

    @PluginMethod
    fun resume(call: PluginCall) {
        positionHandler.post { controller?.play() }
        call.resolve()
    }

    @PluginMethod
    fun seek(call: PluginCall) {
        val ms = call.getLong("ms")
        if (ms == null) {
            call.reject("ms is required")
            return
        }
        positionHandler.post { controller?.seekTo(ms) }
        call.resolve()
    }

    @PluginMethod
    fun stop(call: PluginCall) {
        positionHandler.post { controller?.stop() }
        stopPositionUpdates()
        call.resolve()
    }

    override fun handleOnDestroy() {
        stopPositionUpdates()
        controller?.release()
        controller = null
        super.handleOnDestroy()
    }
}
