package com.audook.app

import android.content.Context
import com.google.android.gms.cast.framework.CastOptions
import com.google.android.gms.cast.framework.OptionsProvider
import com.google.android.gms.cast.framework.SessionProvider
import com.google.android.gms.cast.framework.media.CastMediaOptions
import com.google.android.gms.cast.framework.media.NotificationOptions

/**
 * Required by the Cast Sender SDK (see the OPTIONS_PROVIDER_CLASS_NAME
 * meta-data in AndroidManifest.xml). Targets the device's built-in default
 * media receiver (DEFAULT_MEDIA_RECEIVER_APPLICATION_ID) - audiobook
 * chapters are plain streamable audio URLs, so no custom receiver app is
 * needed, unlike apps with their own branded Cast UI.
 */
class AudookCastOptionsProvider : OptionsProvider {
    override fun getCastOptions(context: Context): CastOptions {
        val notificationOptions = NotificationOptions.Builder().build()
        val mediaOptions = CastMediaOptions.Builder()
            .setNotificationOptions(notificationOptions)
            .build()

        return CastOptions.Builder()
            .setReceiverApplicationId(com.google.android.gms.cast.CastMediaControlIntent.DEFAULT_MEDIA_RECEIVER_APPLICATION_ID)
            .setCastMediaOptions(mediaOptions)
            .setStopReceiverApplicationWhenEndingSession(true)
            .build()
    }

    override fun getAdditionalSessionProviders(context: Context): List<SessionProvider>? = null
}
