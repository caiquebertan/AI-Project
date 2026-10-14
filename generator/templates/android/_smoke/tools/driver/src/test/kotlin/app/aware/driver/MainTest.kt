// {{header}}
package app.aware.driver

import org.junit.Assert.assertEquals
import org.junit.Test

class MainTest {
    @Test
    fun `PLAT-ANDROID-031 smoke driver prints one JSON line`() {
        assertEquals("""{"name":"x","probe_count":1}""", probeLine(arrayOf("x")))
    }
}
