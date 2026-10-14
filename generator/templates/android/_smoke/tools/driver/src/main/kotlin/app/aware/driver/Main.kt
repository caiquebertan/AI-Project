// {{header}}
package app.aware.driver

import app.aware.core.protocol.Probe
import app.aware.core.protocol.ProbeCodec

fun probeLine(args: Array<String>): String = ProbeCodec.encode(Probe(args.firstOrNull() ?: "driver", args.size))

fun main(args: Array<String>) {
    println(probeLine(args))
}
