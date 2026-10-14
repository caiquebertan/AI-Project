// {{header}}
package app.aware.feature.probe

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.lifecycle.ViewModel
import app.aware.core.protocol.ProbeSource
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

const val PROBE_TAG = "probe-label"

@HiltViewModel
class ProbeViewModel @Inject constructor(source: ProbeSource) : ViewModel() {
    private val state = MutableStateFlow(source.label())
    val label: StateFlow<String> = state.asStateFlow()
}

@Composable
fun ProbeScreen(label: String, modifier: Modifier = Modifier) {
    Text(text = label, modifier = modifier.testTag(PROBE_TAG))
}
