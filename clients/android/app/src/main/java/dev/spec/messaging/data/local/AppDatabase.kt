package dev.spec.messaging.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import dev.spec.messaging.domain.*

@Entity(tableName = "messages", indices = [Index(value = ["message_id"], unique = true)])
data class MessageEntity(
    @PrimaryKey(autoGenerate = true) val sequence: Long = 0,
    @ColumnInfo(name = "message_id") val messageId: String,
    val sender: String, val recipient: String, val text: String,
    @ColumnInfo(name = "created_at") val createdAt: String,
    @ColumnInfo(name = "delivery_state") val deliveryState: String,
    val incomingOrder: Long? = null
) {
    fun domain() = Message(messageId, sender, recipient, text, createdAt, DeliveryState.valueOf(deliveryState))
}
@Entity(tableName = "settings")
data class SettingsEntity(@PrimaryKey val id: Int = 1, val name: String? = null, val offline: Boolean = false)

@Dao
interface MessageDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(message: MessageEntity): Long
    @Query("SELECT * FROM messages WHERE message_id = :id")
    suspend fun find(id: String): MessageEntity?
    @Query("SELECT * FROM messages WHERE sender = :user AND delivery_state = 'PENDING' ORDER BY sequence")
    suspend fun pending(user: String): List<MessageEntity>
    @Query("UPDATE messages SET delivery_state = :state WHERE message_id = :id")
    suspend fun updateState(id: String, state: String)
    @Query("UPDATE messages SET delivery_state = 'PENDING' WHERE delivery_state = 'SENDING'")
    suspend fun recoverSending()
    // Received messages retain server order even if their clocks are skewed.
    @Query("SELECT * FROM messages WHERE (sender = :user AND recipient = :other) OR (sender = :other AND recipient = :user) ORDER BY CASE WHEN incomingOrder IS NULL THEN 0 ELSE 1 END, incomingOrder, sequence")
    fun conversation(user: String, other: String): Flow<List<MessageEntity>>
    @Query("UPDATE messages SET incomingOrder = :position WHERE message_id = :id")
    suspend fun incomingOrder(id: String, position: Long)
    @Query("SELECT * FROM settings WHERE id = 1")
    suspend fun settings(): SettingsEntity?
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveSettings(settings: SettingsEntity)
}
@Database(entities = [MessageEntity::class, SettingsEntity::class], version = 1, exportSchema = true)
abstract class AppDatabase : RoomDatabase() { abstract fun messages(): MessageDao }
