// {{header}}
package app.aware.core.data

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import app.aware.core.protocol.ProbeSource
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Entity(tableName = "probe_item")
data class ProbeItem(@PrimaryKey val id: String, val position: Long)

@Dao
interface ProbeDao {
    @Insert
    suspend fun insert(item: ProbeItem)

    @Query("SELECT * FROM probe_item ORDER BY position")
    suspend fun all(): List<ProbeItem>
}

@Database(entities = [ProbeItem::class], version = 1, exportSchema = false)
abstract class ProbeDatabase : RoomDatabase() {
    abstract fun dao(): ProbeDao
}

class RoomProbeSource(private val database: ProbeDatabase) : ProbeSource {
    override fun label(): String = "room:" + database.javaClass.simpleName
}

@Module
@InstallIn(SingletonComponent::class)
object ProbeModule {
    @Provides
    @Singleton
    fun database(@ApplicationContext context: Context): ProbeDatabase =
        Room.databaseBuilder(context, ProbeDatabase::class.java, "probe.db").build()

    @Provides
    fun source(database: ProbeDatabase): ProbeSource = RoomProbeSource(database)
}
