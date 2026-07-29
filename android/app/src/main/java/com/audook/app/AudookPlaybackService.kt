package com.audook.app

import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService

/**
 * Foreground service hosting the single ExoPlayer + MediaSession instance.
 * MediaSessionService automatically promotes itself to a foreground service
 * with a lock-screen/notification-shade media notification while a session
 * is active, and keeps playing when the app is backgrounded or the screen
 * is locked - the standard pattern for background audio on Android.
 */
class AudookPlaybackService : MediaSessionService() {

    private var mediaSession: MediaSession? = null

    override fun onCreate() {
        super.onCreate()
        val player = ExoPlayer.Builder(this).build()
        mediaSession = MediaSession.Builder(this, player).build()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? {
        return mediaSession
    }

    override fun onDestroy() {
        mediaSession?.run {
            player.release()
            release()
            mediaSession = null
        }
        super.onDestroy()
    }
}
