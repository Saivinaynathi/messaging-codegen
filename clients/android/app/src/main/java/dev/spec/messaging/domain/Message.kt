package dev.spec.messaging.domain

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow

enum class DeliveryState { PENDING, SENDING, SENT, RECEIVED }
data class Message(val messageId: String, val sender: String, val recipient: String,
    val text: String, val createdAt: String, val deliveryState: DeliveryState)
data class Settings(val name: String? = null, val offline: Boolean = false)
interface MessageRepository {
    val settings: StateFlow<Settings>
    val error: StateFlow<String?>
    suspend fun initialize()
    suspend fun register(name: String)
    suspend fun createMessage(recipient: String, text: String)
    suspend fun setOffline(offline: Boolean)
    suspend fun synchronize()
    fun conversation(recipient: String): Flow<List<Message>>
}
