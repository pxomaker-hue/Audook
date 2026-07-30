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

    // On a cold app start, the MediaController/session/player pipeline is
    // still spinning up when play() is first called - setMediaItem's own
    // startPositionMs argument (see play() below) is supposed to be honored
    // regardless of that, but has been observed to get silently dropped on
    // this exact cold-start path, resuming from 0 despite the correct
    // chapter being picked. This is a belt-and-suspenders correction: once
    // the player actually reaches STATE_READY, re-assert the intended
    // position if it hasn't drifted there on its own.
    private var pendingResumeMs: Long? = null

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
            // Only the very last chapter in the playlist reaches ENDED -
            // ExoPlayer auto-advances through every earlier one on its own
            // (see play() below), which is what makes chapter transitions
            // survive the WebView being suspended in the background/screen
            // off. Before this, the JS side alone decided "what's next and
            // play it" on every chapter end, which never ran while
            // backgrounded, so playback just silently stopped there.
            if (playbackState == Player.STATE_ENDED) {
                val data = JSObject()
                data.put("ended", true)
                notifyListeners("ended", data)
            }
            if (playbackState == Player.STATE_READY) {
                pendingResumeMs?.let { target ->
                    pendingResumeMs = null
                    val c = controller
                    // A few seconds of drift is normal playback progress
                    // since setMediaItem was called - only correct an
                    // actual reset-to-0, don't fight legitimate playback.
                    if (c != null && target > 3000 && c.currentPosition < 1000) {
                        c.seekTo(target)
                    }
                }
            }
        }

        // Fires on every chapter change - both ExoPlayer's own automatic
        // advance at the end of a chapter, and a manual previousChapter()/
        // nextChapter() call. The JS side has no other way to learn which
        // chapter is now playing once the native playlist advances on its
        // own without it.
        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
            val c = controller ?: return
            val data = JSObject()
            data.put("chapterIndex", c.currentMediaItemIndex)
            notifyListeners("chapterChanged", data)
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
        val chaptersArray = call.getArray("chapters")
        val startIndex = call.getInt("startIndex") ?: 0
        val cover = call.getString("cover")
        // PluginCall.getLong() only returns a value if it's already boxed as
        // a Java Long - a JS number arrives as Integer or Double instead, so
        // this always silently returned null here. getDouble() handles both,
        // and is why resuming a book always restarted from 0.
        val startPositionMs = call.getDouble("positionMs")?.toLong() ?: 0L

        if (chaptersArray == null || chaptersArray.length() == 0) {
            call.reject("chapters is required")
            return
        }

        val c = controller
        if (c == null) {
            call.reject("Player not ready")
            return
        }

        // The whole book's chapters are handed to ExoPlayer as one playlist
        // (instead of a single chapter re-played on every transition) so it
        // can advance through them entirely on its own. That's what makes
        // auto-advance survive the WebView being suspended in the
        // background/screen off - see onPlaybackStateChanged above.
        val mediaItems = mutableListOf<MediaItem>()
        for (i in 0 until chaptersArray.length()) {
            val chapter = chaptersArray.getJSONObject(i)
            val chapterTitle = chapter.optString("title", "")
            val metadataBuilder = MediaMetadata.Builder().setTitle(chapterTitle)
            if (cover != null) {
                metadataBuilder.setArtworkUri(android.net.Uri.parse(cover))
            }
            mediaItems.add(
                MediaItem.Builder()
                    .setUri(chapter.getString("url"))
                    .setMediaMetadata(metadataBuilder.build())
                    .build()
            )
        }

        // MediaController must only be touched from the thread that built it
        // (the main thread here, via positionHandler) - Capacitor plugin
        // methods run on their own "CapacitorPlugins" handler thread, which
        // crashed the app with IllegalStateException before this dispatch.
        //
        // The resume position is passed to setMediaItems() itself rather
        // than a separate seekTo() call afterward - a seek issued right
        // after prepare() can arrive before the player has finished loading
        // the item and get silently dropped/reset once it becomes ready,
        // which is why resuming a book on mobile always restarted from 0.
        pendingResumeMs = if (startPositionMs > 0) startPositionMs else null
        positionHandler.post {
            c.setMediaItems(mediaItems, startIndex, startPositionMs)
            c.prepare()
            c.play()
        }
        call.resolve()
    }

    @PluginMethod
    fun previousChapter(call: PluginCall) {
        // The "MediaItem" variant always jumps to the actual previous
        // playlist entry (or does nothing at the first one) - unlike plain
        // seekToPrevious(), which restarts the current item instead once
        // playback is a few seconds in. Chapter buttons always mean "go to
        // that chapter", never "restart this one".
        positionHandler.post { controller?.seekToPreviousMediaItem() }
        call.resolve()
    }

    @PluginMethod
    fun nextChapter(call: PluginCall) {
        positionHandler.post { controller?.seekToNextMediaItem() }
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
        // Same getLong() pitfall as play()'s positionMs above - this was
        // silently rejecting every seek call (the ±30s buttons never
        // actually moved playback on mobile).
        val ms = call.getDouble("ms")?.toLong()
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
