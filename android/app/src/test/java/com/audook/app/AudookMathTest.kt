package com.audook.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AudookMathTest {
    private val eps = 0.0001f

    // ---- remainingSeconds ----

    @Test fun remainingSecondsFloorsToWholeSeconds() {
        assertEquals(90L, AudookMath.remainingSeconds(endTimeMs = 100_000, nowMs = 10_000))
        assertEquals(1L, AudookMath.remainingSeconds(endTimeMs = 11_999, nowMs = 10_000))
        assertEquals(0L, AudookMath.remainingSeconds(endTimeMs = 10_999, nowMs = 10_000))
    }

    @Test fun remainingSecondsNeverGoesNegative() {
        assertEquals(0L, AudookMath.remainingSeconds(endTimeMs = 10_000, nowMs = 25_000))
    }

    // ---- sleep timer fade ----

    @Test fun noFadeUntilTheLastTwentySeconds() {
        assertEquals(1f, AudookMath.sleepFadeFactor(3600), eps)
        assertEquals(1f, AudookMath.sleepFadeFactor(21), eps)
        assertEquals(1f, AudookMath.sleepFadeFactor(20), eps)
    }

    @Test fun fadeIsLinearDownToSilence() {
        assertEquals(0.5f, AudookMath.sleepFadeFactor(10), eps)
        assertEquals(0.05f, AudookMath.sleepFadeFactor(1), eps)
        assertEquals(0f, AudookMath.sleepFadeFactor(0), eps)
    }

    @Test fun fadeStaysInsideZeroToOne() {
        assertEquals(0f, AudookMath.sleepFadeFactor(-5), eps)
    }

    @Test fun fadeNeverIncreasesAsTimeRunsOut() {
        var previous = 1f
        for (remaining in 25L downTo 0L) {
            val factor = AudookMath.sleepFadeFactor(remaining)
            assertTrue("fade went up at $remaining s", factor <= previous + eps)
            previous = factor
        }
    }

    @Test fun fadeLengthMatchesTheDesktopTimer() {
        // SLEEP_TIMER_FADE_SECONDS in app/services/player_service.py
        assertEquals(20L, AudookMath.SLEEP_TIMER_FADE_SECONDS)
    }

    @Test fun customFadeLength() {
        assertEquals(0.5f, AudookMath.sleepFadeFactor(remainingSeconds = 5, fadeSeconds = 10), eps)
    }

    // ---- loudness gain -> player volume ----

    @Test fun noOrPositiveGainLeavesTheVolumeAtUnity() {
        assertEquals(1f, AudookMath.linearVolumeForGainDb(0f), eps)
        assertEquals(1f, AudookMath.linearVolumeForGainDb(6f), eps)
    }

    @Test fun negativeGainAttenuatesLikeDecibels() {
        assertEquals(0.5012f, AudookMath.linearVolumeForGainDb(-6f), 0.001f)
        assertEquals(0.1f, AudookMath.linearVolumeForGainDb(-20f), eps)
    }

    @Test fun extremeNegativeGainStaysInRange() {
        val v = AudookMath.linearVolumeForGainDb(-200f)
        assertTrue(v >= 0f && v < 0.0001f)
    }
}
