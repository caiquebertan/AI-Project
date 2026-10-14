// {{header}}
package app.aware.core.protocol

class FakeProbeSource(private val value: String) : ProbeSource {
    override fun label(): String = value
}
