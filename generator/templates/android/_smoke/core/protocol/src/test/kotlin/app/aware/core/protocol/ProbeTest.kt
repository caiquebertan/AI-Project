// {{header}}
package app.aware.core.protocol

import java.io.File
import kotlinx.coroutines.async
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProbeTest {
    @Test
    fun `PLAT-ANDROID-023 smoke id is carried in the JUnit report`() {
        val probe = Probe("a", 2)
        assertEquals("""{"name":"a","probe_count":2}""", ProbeCodec.encode(probe))
        assertEquals(probe, ProbeCodec.decode("""{"name":"a","probe_count":2,"extra":true}"""))
    }

    @Test
    fun `PLAT-ANDROID-021 smoke repo root is visible to tests`() {
        val root = System.getProperty("aware.repoRoot")
        assertNotNull(root)
        assertTrue(File(root, "spec/README.md").isFile)
    }

    @Test
    fun `PLAT-ANDROID-019 smoke virtual time and test fixtures`() = runTest {
        val result = async { delayedLabel(FakeProbeSource("x"), 5_000) }
        advanceTimeBy(5_001)
        assertEquals("x", result.await())
    }
}
