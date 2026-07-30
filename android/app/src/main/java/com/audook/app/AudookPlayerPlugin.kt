package com.audook.app

import android.content.ComponentName
import android.media.audiofx.DynamicsProcessing
import android.media.audiofx.Equalizer
import android.media.audiofx.LoudnessEnhancer
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.PlaybackParameters
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.google.common.util.concurrent.MoreExecutors
import kotlin.math.abs
import kotlin.math.pow

// Standard 10-band ISO graphic EQ center frequencies (Hz) - matches VLC's
// own AudioEqualizer band layout, which the desktop presets
// (EqualizerPresetRepository, 10 bands + preamp) are built against. Android's
// own Equalizer effect exposes a different (usually smaller, device-
// dependent) number of bands, so each desktop band is mapped onto whichever
// Android band's own center frequency is closest - an approximation, not an
// exact match, since the two don't line up 1:1.
private val DESKTOP_EQ_FREQUENCIES = listOf(31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)

// Same three intensities as COMPRESSOR_PRESETS in app/player/vlc_player.py -
// approximate, not identical: Android's DynamicsProcessing multi-band
// compressor (API 28+) is a different algorithm than VLC's own "compressor"
// filter, tuned here with the same threshold/ratio/attack/release/makeup-
// gain numbers to land in the same ballpark rather than reproduce it exactly.
private data class CompressionPreset(
    val thresholdDb: Float,
    val ratio: Float,
    val attackMs: Float,
    val releaseMs: Float,
    val makeupGainDb: Float
)

private val COMPRESSION_PRESETS = mapOf(
    "leger" to CompressionPreset(thresholdDb = -15f, ratio = 2f, attackMs = 25f, releaseMs = 150f, makeupGainDb = 3f),
    "modere" to CompressionPreset(thresholdDb = -18f, ratio = 3f, attackMs = 20f, releaseMs = 120f, makeupGainDb = 5f),
    "fort" to CompressionPreset(thresholdDb = -22f, ratio = 4.5f, attackMs = 15f, releaseMs = 100f, makeupGainDb = 7f)
)

// DynamicsProcessing needs its channel count fixed at construction time -
// audiobooks are effectively always mono or stereo, and stereo is the safer
// assumption (a mono session opened as stereo generally still works; the
// reverse can throw).
private const val COMPRESSION_CHANNEL_COUNT = 2

private const val TAG = "AudookAudioFx"

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

    // Audio effects, attached to ExoPlayer's own audio session id - built
    // fresh whenever that id changes (a new one can be assigned when the
    // playback service's underlying player is recreated), and re-applied
    // from the "desired" fields below each time, since a freshly created
    // effect instance always starts back at its flat/off default.
    private var equalizer: Equalizer? = null
    private var loudnessEnhancer: LoudnessEnhancer? = null
    private var dynamicsProcessing: DynamicsProcessing? = null
    private var lastAudioSessionId: Int = 0
    private var desiredEqBands: FloatArray? = null // 10 values, dB - null means off
    private var desiredEqPreamp: Float = 0f
    private var desiredLoudnessGainDb: Float = 0f
    private var desiredCompressionPreset: String? = null

    // Chromecast/Google Home - fully independent of the local ExoPlayer;
    // see AudookCastManager for why the local playlist stays loaded (paused,
    // silent) while casting instead of being torn down.
    private lateinit var castManager: AudookCastManager
    private var lastKnownRemotePlaying: Boolean = false
    // Mirrors whatever emitPosition() last saw from the cast device, polled
    // once a second - kept independently of AudookCastManager's own idea of
    // "last position" because by the time a session actually ends, the
    // receiver has often already quit and is reporting a stale/zeroed
    // position, which would otherwise overwrite the real one right before
    // we need it to resume local playback.
    private var lastSeenCastPositionMs: Long = 0L

    override fun load() {
        val sessionToken = SessionToken(
            context,
            ComponentName(context, AudookPlaybackService::class.java)
        )
        val future = MediaController.Builder(context, sessionToken).buildAsync()
        future.addListener({
            controller = future.get()
            controller?.addListener(playerListener)
            // AudookPlaybackService generates and assigns this itself now
            // (instead of leaving ExoPlayer to auto-generate one and report
            // it via onAudioSessionIdChanged, which never actually fired in
            // practice) - always available immediately, no need to wait for
            // playback to start or for a callback that wasn't arriving.
            ensureAudioEffects(AudookPlaybackService.audioSessionId)
        }, MoreExecutors.directExecutor())

        castManager = AudookCastManager(context)
        castManager.listener = object : AudookCastManager.Listener {
            override fun onDevicesChanged(devices: List<AudookCastManager.CastDeviceInfo>) {
                val data = JSObject()
                val arr = JSArray()
                for (d in devices) {
                    val obj = JSObject()
                    obj.put("id", d.id)
                    obj.put("name", d.name)
                    arr.put(obj)
                }
                data.put("devices", arr)
                notifyListeners("castDevicesChanged", data)
            }

            override fun onCastStateChanged(isCasting: Boolean, deviceName: String?) {
                val data = JSObject()
                data.put("isCasting", isCasting)
                data.put("deviceName", deviceName)
                notifyListeners("castStateChanged", data)
                if (isCasting) {
                    // Hand off whatever's currently parked on locally to the
                    // cast device, from wherever local playback had reached.
                    positionHandler.post {
                        val c = controller ?: return@post
                        c.pause()
                        lastSeenCastPositionMs = c.currentPosition
                        loadCurrentChapterOnCast(c.currentPosition)
                    }
                } else {
                    // Resume locally from wherever the cast device had
                    // reached, so switching back doesn't restart the chapter.
                    // Read the position before stopDiscovery/detach can null
                    // it out any further, and mirror whatever play/pause
                    // state the cast device was last in - otherwise the local
                    // player stays paused (from the pause() issued when the
                    // cast session started) while the UI still thinks it's
                    // playing, frozen at the stale 0:00 it never left.
                    val freshMs = castManager.getPositionMs()
                    val resumeMs = if (freshMs > 0) freshMs else lastSeenCastPositionMs
                    val wasPlaying = this@AudookPlayerPlugin.lastKnownRemotePlaying
                    positionHandler.post {
                        val c = controller ?: return@post
                        c.seekTo(resumeMs)
                        if (wasPlaying) {
                            c.play()
                            startPositionUpdates()
                        } else {
                            stopPositionUpdates()
                        }
                        emitPosition()
                    }
                }
            }

            override fun onRemotePlayingChanged(isPlaying: Boolean) {
                lastKnownRemotePlaying = isPlaying
                if (isPlaying) startPositionUpdates() else stopPositionUpdates()
                val data = JSObject()
                data.put("isPlaying", isPlaying)
                notifyListeners("stateChange", data)
            }

            override fun onRemoteChapterEnded() {
                // Mirrors the local STATE_ENDED handling: advance the
                // (paused, silent) local playlist so both the chapter index
                // bookkeeping and the "was this the last chapter" check stay
                // exactly the same as local playback, then mirror the new
                // current item to the cast device.
                positionHandler.post {
                    val c = controller ?: return@post
                    val wasLastChapter = c.currentMediaItemIndex >= c.mediaItemCount - 1
                    if (wasLastChapter) {
                        val data = JSObject()
                        data.put("ended", true)
                        notifyListeners("ended", data)
                    } else {
                        c.seekToNextMediaItem()
                        loadCurrentChapterOnCast(0)
                    }
                }
            }
        }
    }

    // Reads whichever chapter the local (paused, silent) ExoPlayer playlist
    // is currently parked on and mirrors it to the cast device - used both
    // when a cast session starts and on every chapter transition while
    // casting (see previousChapter/nextChapter and onRemoteChapterEnded).
    private fun loadCurrentChapterOnCast(positionMs: Long) {
        val c = controller ?: return
        val item = c.currentMediaItem ?: return
        val url = item.localConfiguration?.uri?.toString() ?: return
        val title = item.mediaMetadata.title?.toString() ?: ""
        castManager.loadMedia(url, title, null, positionMs)
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

        override fun onAudioSessionIdChanged(audioSessionId: Int) {
            Log.d(TAG, "onAudioSessionIdChanged: $audioSessionId")
            ensureAudioEffects(audioSessionId)
        }
    }

    // Rebuilds the Equalizer/LoudnessEnhancer against a new audio session id
    // and re-applies whatever the JS side last asked for - called whenever
    // ExoPlayer reports a session id (once playback actually starts, and
    // again if it's ever regenerated), since audio effects only work
    // attached to a real, current session id.
    private fun ensureAudioEffects(sessionId: Int) {
        if (sessionId == 0 || sessionId == lastAudioSessionId) {
            Log.d(TAG, "ensureAudioEffects: skipped (sessionId=$sessionId, lastAudioSessionId=$lastAudioSessionId)")
            return
        }
        lastAudioSessionId = sessionId

        try {
            equalizer?.release()
        } catch (e: Exception) { /* already released or invalid - fine */ }
        try {
            equalizer = Equalizer(0, sessionId)
            Log.d(TAG, "Equalizer created for session $sessionId, bands=${equalizer?.numberOfBands}, range=${equalizer?.bandLevelRange?.toList()}")
        } catch (e: Exception) {
            Log.w(TAG, "Failed to create Equalizer for session $sessionId", e)
            equalizer = null
        }

        try {
            loudnessEnhancer?.release()
        } catch (e: Exception) { /* already released or invalid - fine */ }
        try {
            loudnessEnhancer = LoudnessEnhancer(sessionId)
        } catch (e: Exception) {
            loudnessEnhancer = null
        }

        try {
            dynamicsProcessing?.release()
        } catch (e: Exception) { /* already released or invalid - fine */ }
        dynamicsProcessing = null
        // A single-band multi-band-compressor stage is configured up front
        // (mbcInUse=true) since DynamicsProcessing's stages can't be added
        // after construction, only reconfigured/enabled - so this has to
        // exist from the start even before the user picks a preset, sitting
        // disabled (see applyCompression) until they do. Assumes a stereo
        // session; a mono one would fail this construction and just leave
        // compression silently unavailable for that book (caught below).
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            try {
                val config = DynamicsProcessing.Config.Builder(
                    DynamicsProcessing.VARIANT_FAVOR_FREQUENCY_RESOLUTION,
                    COMPRESSION_CHANNEL_COUNT,
                    false, 0,
                    true, 1,
                    false, 0,
                    false
                ).build()
                dynamicsProcessing = DynamicsProcessing(0, sessionId, config)
            } catch (e: Exception) {
                dynamicsProcessing = null
            }
        }

        applyEqualizer()
        applyLoudnessGain()
        applyCompression()
    }

    // Maps the 10 desktop-style dB values onto however many bands this
    // device's Equalizer effect actually has, each one taking the nearest
    // desktop band by center frequency - see DESKTOP_EQ_FREQUENCIES.
    private fun applyEqualizer() {
        val eq = equalizer
        if (eq == null) {
            Log.w(TAG, "applyEqualizer: no Equalizer instance (creation failed or no session yet)")
            return
        }
        val bands = desiredEqBands
        if (bands == null) {
            try { eq.enabled = false } catch (e: Exception) { }
            Log.d(TAG, "applyEqualizer: disabled")
            return
        }
        try {
            val range = eq.bandLevelRange
            val numBands = eq.numberOfBands.toInt()
            val applied = mutableListOf<String>()
            for (androidBand in 0 until numBands) {
                val centerFreqHz = eq.getCenterFreq(androidBand.toShort()) / 1000
                var bestIdx = 0
                var bestDiff = Int.MAX_VALUE
                for ((i, freq) in DESKTOP_EQ_FREQUENCIES.withIndex()) {
                    val diff = abs(freq - centerFreqHz)
                    if (diff < bestDiff) {
                        bestDiff = diff
                        bestIdx = i
                    }
                }
                val gainDb = (bands.getOrElse(bestIdx) { 0f }) + desiredEqPreamp
                val millibels = (gainDb * 100)
                    .toInt()
                    .coerceIn(range[0].toInt(), range[1].toInt())
                eq.setBandLevel(androidBand.toShort(), millibels.toShort())
                applied.add("band$androidBand(${centerFreqHz}Hz)=${millibels}mB")
            }
            eq.enabled = true
            Log.d(TAG, "applyEqualizer: enabled=${eq.enabled}, $applied")
        } catch (e: Exception) {
            // Effect exists but a device-specific quirk rejected a band/
            // range value - leave whatever was already applied rather than
            // crash the plugin over a cosmetic feature.
            Log.w(TAG, "applyEqualizer failed", e)
        }
    }

    // Positive gain (boosting a quiet book) goes through LoudnessEnhancer,
    // the Android effect actually meant for gain beyond unity - its own
    // volume control can only attenuate (0..1), never amplify. Negative
    // gain (a book already mastered loud) goes through the player's own
    // volume instead, converting dB to the linear scale it expects.
    private fun applyLoudnessGain() {
        val gainDb = desiredLoudnessGainDb
        if (gainDb > 0f) {
            try {
                loudnessEnhancer?.setTargetGain((gainDb * 100).toInt())
                loudnessEnhancer?.enabled = true
            } catch (e: Exception) { }
            positionHandler.post { controller?.volume = 1f }
        } else {
            try { loudnessEnhancer?.enabled = false } catch (e: Exception) { }
            val linear = 10.0.pow(gainDb / 20.0).toFloat().coerceIn(0f, 1f)
            positionHandler.post { controller?.volume = linear }
        }
    }

    // Applies (or disables) the single-band MBC stage configured at
    // construction time (see ensureAudioEffects) using the same threshold/
    // ratio/attack/release/makeup-gain numbers as VLC's compressor presets -
    // an approximation given the different underlying algorithm, not a
    // reproduction of VLC's own filter.
    private fun applyCompression() {
        val dp = dynamicsProcessing ?: return
        val presetKey = desiredCompressionPreset
        if (presetKey == null) {
            try { dp.setEnabled(false) } catch (e: Exception) { }
            return
        }
        val preset = COMPRESSION_PRESETS[presetKey] ?: return
        try {
            for (channel in 0 until COMPRESSION_CHANNEL_COUNT) {
                val mbcBand = DynamicsProcessing.MbcBand(
                    true, // enabled
                    0f, // cutoffFrequency - only band, covers the whole spectrum
                    preset.attackMs,
                    preset.releaseMs,
                    preset.ratio,
                    preset.thresholdDb,
                    3f, // kneeWidth
                    -80f, // noiseGateThreshold
                    1f, // expanderRatio
                    0f, // preGain
                    preset.makeupGainDb // postGain
                )
                dp.setMbcBandByChannelIndex(channel, 0, mbcBand)
            }
            dp.setEnabled(true)
        } catch (e: Exception) {
            // Device-specific quirk rejected a parameter - leave whatever
            // was already applied rather than crash over a cosmetic feature.
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
        val data = JSObject()
        if (castManager.isCasting()) {
            val posMs = castManager.getPositionMs()
            if (posMs > 0) lastSeenCastPositionMs = posMs
            data.put("positionMs", posMs)
            data.put("durationMs", castManager.getDurationMs())
        } else {
            val c = controller ?: return
            data.put("positionMs", c.currentPosition)
            data.put("durationMs", if (c.duration > 0) c.duration else 0)
        }
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
            // While casting, the local playlist is only kept as a silent
            // source of truth for chapter sequencing (see
            // AudookCastManager's class doc) - actual sound comes from the
            // cast device instead.
            if (castManager.isCasting()) {
                loadCurrentChapterOnCast(startPositionMs)
            } else {
                c.play()
            }
        }
        call.resolve()
    }

    @PluginMethod
    fun setSpeed(call: PluginCall) {
        val speed = call.getDouble("speed")?.toFloat()
        if (speed == null) {
            call.reject("speed is required")
            return
        }
        // PlaybackParameters is a player-level property, not tied to the
        // current MediaItem - it carries over automatically across chapter
        // transitions within the playlist, no need to re-apply it per chapter.
        positionHandler.post { controller?.playbackParameters = PlaybackParameters(speed) }
        call.resolve()
    }

    @PluginMethod
    fun setEqualizer(call: PluginCall) {
        val bandsArray: JSArray? = call.getArray("bands")
        val preamp = call.getFloat("preamp") ?: 0f
        desiredEqBands = if (bandsArray == null) {
            null
        } else {
            FloatArray(bandsArray.length()) { i -> bandsArray.getDouble(i).toFloat() }
        }
        desiredEqPreamp = preamp
        Log.d(TAG, "setEqualizer called: bands=${desiredEqBands?.toList()}, preamp=$preamp, hasEqualizerInstance=${equalizer != null}")
        applyEqualizer()
        call.resolve()
    }

    @PluginMethod
    fun setLoudnessGain(call: PluginCall) {
        val gainDb = call.getFloat("gainDb") ?: 0f
        desiredLoudnessGainDb = gainDb
        applyLoudnessGain()
        call.resolve()
    }

    @PluginMethod
    fun setCompression(call: PluginCall) {
        val preset = call.getString("preset")
        desiredCompressionPreset = if (preset.isNullOrEmpty()) null else preset
        applyCompression()
        call.resolve()
    }

    @PluginMethod
    fun previousChapter(call: PluginCall) {
        // The "MediaItem" variant always jumps to the actual previous
        // playlist entry (or does nothing at the first one) - unlike plain
        // seekToPrevious(), which restarts the current item instead once
        // playback is a few seconds in. Chapter buttons always mean "go to
        // that chapter", never "restart this one". Always applied to the
        // local playlist (even while casting - see AudookCastManager's
        // class doc) so it stays the single source of truth for the index.
        positionHandler.post {
            controller?.seekToPreviousMediaItem()
            if (castManager.isCasting()) loadCurrentChapterOnCast(0)
        }
        call.resolve()
    }

    @PluginMethod
    fun nextChapter(call: PluginCall) {
        positionHandler.post {
            controller?.seekToNextMediaItem()
            if (castManager.isCasting()) loadCurrentChapterOnCast(0)
        }
        call.resolve()
    }

    @PluginMethod
    fun pause(call: PluginCall) {
        if (castManager.isCasting()) {
            castManager.pause()
        } else {
            positionHandler.post { controller?.pause() }
        }
        call.resolve()
    }

    @PluginMethod
    fun resume(call: PluginCall) {
        if (castManager.isCasting()) {
            castManager.resume()
        } else {
            positionHandler.post { controller?.play() }
        }
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
        if (castManager.isCasting()) {
            castManager.seek(ms)
        } else {
            positionHandler.post { controller?.seekTo(ms) }
        }
        call.resolve()
    }

    // MediaRouter/CastContext calls (all four methods below) must run on the
    // main thread, same as MediaController - Capacitor plugin methods run
    // on their own background thread by default, which was silently
    // swallowed by AudookCastManager's broad try/catch, so scanning/
    // connecting never actually did anything.
    @PluginMethod
    fun scanCastDevices(call: PluginCall) {
        positionHandler.post { castManager.startDiscovery() }
        call.resolve()
    }

    @PluginMethod
    fun stopCastDiscovery(call: PluginCall) {
        positionHandler.post { castManager.stopDiscovery() }
        call.resolve()
    }

    @PluginMethod
    fun connectCastDevice(call: PluginCall) {
        val deviceId = call.getString("deviceId")
        if (deviceId == null) {
            call.reject("deviceId is required")
            return
        }
        positionHandler.post {
            if (!castManager.connect(deviceId)) {
                call.reject("Device not found")
            } else {
                call.resolve()
            }
        }
    }

    @PluginMethod
    fun disconnectCastDevice(call: PluginCall) {
        positionHandler.post { castManager.disconnect() }
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
        try { equalizer?.release() } catch (e: Exception) { }
        try { loudnessEnhancer?.release() } catch (e: Exception) { }
        try { dynamicsProcessing?.release() } catch (e: Exception) { }
        if (::castManager.isInitialized) castManager.stopDiscovery()
        controller?.release()
        controller = null
        super.handleOnDestroy()
    }
}
