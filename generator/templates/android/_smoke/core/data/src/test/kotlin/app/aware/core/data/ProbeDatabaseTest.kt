// {{header}}
package app.aware.core.data

import android.content.Context
import androidx.room.Room
import androidx.room.withTransaction
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config

@RunWith(AndroidJUnit4::class)
@Config(sdk = [35])
class ProbeDatabaseTest {
    @Test
    fun `PLAT-ANDROID-012 smoke in-memory Room transaction under Robolectric`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val db = Room.inMemoryDatabaseBuilder(context, ProbeDatabase::class.java).allowMainThreadQueries().build()
        try {
            val ids = runBlocking {
                db.withTransaction {
                    db.dao().insert(ProbeItem("b", 2))
                    db.dao().insert(ProbeItem("a", 1))
                }
                db.dao().all().map { it.id }
            }
            assertEquals(listOf("a", "b"), ids)
        } finally {
            db.close()
        }
    }

    @Test
    fun `PLAT-ANDROID-013 smoke BuildConfig server URL is defined`() {
        assertTrue(BuildConfig.SERVER_BASE_URL.startsWith("http://"))
    }
}
