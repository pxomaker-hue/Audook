package com.audook.app

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * The Chromecast default receiver silently refuses media loaded with the wrong
 * content type (it used to be hardcoded to audio/mpeg, which broke every .m4b).
 * Keep in sync with CONTENT_TYPES in app/cast/cast_player.py.
 */
class CastContentTypeTest {
    @Test fun audiobookFormats() {
        assertEquals("audio/mp4", guessContentType("http://x/book.m4b"))
        assertEquals("audio/mp4", guessContentType("http://x/book.M4A"))
        assertEquals("audio/mpeg", guessContentType("http://x/book.mp3"))
        assertEquals("audio/flac", guessContentType("http://x/book.flac"))
        assertEquals("audio/ogg", guessContentType("http://x/book.opus"))
        assertEquals("audio/wav", guessContentType("http://x/book.wav"))
        assertEquals("audio/aac", guessContentType("http://x/book.aac"))
    }

    @Test fun directUrlsUseTheExtensionOfTheUrlPath() {
        assertEquals("audio/mpeg", guessContentType("http://x/a.mp3?token=abc"))
        assertEquals("audio/mp4", guessContentType("https://plex.example/library/parts/1/file.m4b"))
    }

    // What the app really sends: the proxy endpoint, file name in the path parameter.
    @Test fun proxyUrlsUseTheExtensionOfThePathParameter() {
        assertEquals("audio/mp4", guessContentType("http://nas:5000/api/cast/local-audio?path=%2Fbooks%2Fa%20b.m4b"))
        assertEquals("audio/flac", guessContentType("http://nas:5000/api/cast/local-audio?path=C%3A%5Cbooks%5Ca.flac"))
        assertEquals("audio/mp4", guessContentType("http://nas:5000/api/cast/local-audio?path=%2Fb%2Fa.m4b&token=tok%20en"))
        assertEquals("audio/mpeg", guessContentType("http://nas:5000/api/cast/local-audio?token=t&path=%2Fb%2Fa.mp3"))
    }

    @Test fun proxyUrlWithAnUpstreamStreamUrlInThePathParameter() {
        assertEquals("audio/mp4", guessContentType("http://nas:5000/api/cast/local-audio?path=http%3A%2F%2Fabs%3A13378%2Fs%2Fitem%2Fx.m4b%3Ftoken%3Dabc"))
    }

    @Test fun malformedEscapeDoesNotCrash() {
        assertEquals("audio/mpeg", guessContentType("http://nas:5000/api/cast/local-audio?path=%ZZ.unknown"))
    }

    @Test fun aFolderNamedLikeAnExtensionIsNotAnExtension() {
        assertEquals("audio/mpeg", guessContentType("http://x/some.dir/stream"))
    }

    @Test fun unknownOrMissingExtensionFallsBackToMpeg() {
        assertEquals("audio/mpeg", guessContentType("http://x/stream"))
        assertEquals("audio/mpeg", guessContentType("http://x/file.unknown"))
    }
}
