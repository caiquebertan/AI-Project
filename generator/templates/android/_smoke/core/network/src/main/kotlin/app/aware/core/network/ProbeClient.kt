// {{header}}
package app.aware.core.network

import app.aware.core.protocol.Probe
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.GET

interface ProbeApi {
    @GET("v1/probe")
    suspend fun probe(): Probe
}

object ProbeClient {
    private val json = Json { ignoreUnknownKeys = true }

    fun create(baseUrl: String): ProbeApi =
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ProbeApi::class.java)
}
