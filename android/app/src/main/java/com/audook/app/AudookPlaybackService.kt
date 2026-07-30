package com.audook.app

import android.content.Context
import android.media.AudioManager
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

    companion object {
        // Generated once here (rather than relying on ExoPlayer to assign
        // and report one of its own via Player.Listener.onAudioSessionIdChanged)
        // and handed to setAudioSessionId() below - AudookPlayerPlugin's
        // equalizer/normalization/compression all need a real session id to
        // attach to, and that callback was never actually firing in
        // practice, silently leaving every audio effect uncreated.
        var audioSessionId: Int = 0
            private set
    }

    override fun onCreate() {
        super.onCreate()
        val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioSessionId = audioManager.generateAudioSessionId()
        val player = ExoPlayer.Builder(this).build()
        player.setAudioSessionId(audioSessionId)
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
