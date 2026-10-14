// {{header}}
package app.aware.core.network

import app.aware.core.protocol.Probe
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Test

class ProbeClientTest {
    @Test
    fun `PLAT-ANDROID-020 smoke MockWebServer round trip`() {
        val server = MockWebServer()
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""{"name":"s","probe_count":1,"extra":true}"""),
        )
        server.start()
        try {
            val api = ProbeClient.create(server.url("/").toString())
            assertEquals(Probe("s", 1), runBlocking { api.probe() })
            assertEquals("/v1/probe", server.takeRequest().path)
        } finally {
            server.shutdown()
        }
    }
}
