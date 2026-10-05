package com.audook.app

import kotlin.math.pow

/**
 * Pure helpers behind the native player's audio features - no Android classes,
 * so they run in plain JVM unit tests (app/src/test).
 */
object AudookMath {
    /** Length of the sleep timer's volume fade-out - same as SLEEP_TIMER_FADE_SECONDS on desktop. */
    const val SLEEP_TIMER_FADE_SECONDS = 20L

    /** Whole seconds left before [endTimeMs]; never negative. */
    fun remainingSeconds(endTimeMs: Long, nowMs: Long): Long = maxOf(0L, (endTimeMs - nowMs) / 1000)

    /**
     * Volume multiplier for the sleep timer: 1 until the last [fadeSeconds], then a
     * linear ramp down to 0 when the timer reaches zero.
     */
    fun sleepFadeFactor(remainingSeconds: Long, fadeSeconds: Long = SLEEP_TIMER_FADE_SECONDS): Float {
        if (remainingSeconds > fadeSeconds) return 1f
        return (remainingSeconds.toFloat() / fadeSeconds.toFloat()).coerceIn(0f, 1f)
    }

    /**
     * Player volume (0..1) for a loudness gain in dB. The player's volume can only
     * attenuate, so positive gain is handled elsewhere (LoudnessEnhancer) and maps to 1.
     */
    fun linearVolumeForGainDb(gainDb: Float): Float {
        if (gainDb >= 0f) return 1f
        return 10.0.pow(gainDb / 20.0).toFloat().coerceIn(0f, 1f)
    }
}
