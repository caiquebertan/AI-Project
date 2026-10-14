// {{header}}
package app.aware.feature.probe

import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.aware.core.protocol.FakeProbeSource
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config

@RunWith(AndroidJUnit4::class)
@Config(sdk = [35])
class ProbeScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun `PLAT-ANDROID-022 smoke Compose test tag under Robolectric with test fixtures`() {
        val source = FakeProbeSource("fake")
        compose.setContent { ProbeScreen(label = source.label()) }
        compose.onNodeWithTag(PROBE_TAG).assertTextEquals("fake")
    }

    @Test
    fun `PLAT-ANDROID-016 smoke view model reads the injected port`() {
        val viewModel = ProbeViewModel(FakeProbeSource("vm"))
        assertEquals("vm", viewModel.label.value)
    }
}
