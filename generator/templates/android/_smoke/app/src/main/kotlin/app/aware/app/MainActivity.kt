// {{header}}
package app.aware.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.aware.feature.probe.ProbeScreen
import app.aware.feature.probe.ProbeViewModel
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val viewModel: ProbeViewModel = hiltViewModel()
            val label by viewModel.label.collectAsStateWithLifecycle()
            MaterialTheme { ProbeScreen(label) }
        }
    }
}
