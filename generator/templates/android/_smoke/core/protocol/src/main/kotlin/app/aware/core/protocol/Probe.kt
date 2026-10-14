// {{header}}
package app.aware.core.protocol

import kotlinx.coroutines.delay
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class Probe(val name: String, @SerialName("probe_count") val count: Int)

object ProbeCodec {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun encode(value: Probe): String = json.encodeToString(Probe.serializer(), value)

    fun decode(text: String): Probe = json.decodeFromString(Probe.serializer(), text)
}

interface ProbeSource {
    fun label(): String
}

suspend fun delayedLabel(source: ProbeSource, waitMs: Long): String {
    delay(waitMs)
    return source.label()
}
