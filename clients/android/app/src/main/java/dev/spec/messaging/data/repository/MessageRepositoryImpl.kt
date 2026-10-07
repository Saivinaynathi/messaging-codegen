package dev.spec.messaging.data.repository

import dev.spec.messaging.data.local.*
import dev.spec.messaging.data.remote.*
import dev.spec.messaging.domain.*
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

@Singleton
class MessageRepositoryImpl @Inject constructor(private val dao: MessageDao, private val api: MessagingApi) : MessageRepository {
    private val mutableSettings = MutableStateFlow(Settings())
    override val settings = mutableSettings.asStateFlow()
    private val mutableError = MutableStateFlow<String?>(null)
    override val error = mutableError.asStateFlow()
    // A mode transition waits for any request already in flight. Once OFFLINE is
    // published, no request can start until an online transition acquires this lock.
    private val network = Mutex()
    private var initialized = false
    override suspend fun initialize() = network.withLock {
        if (!initialized) {
            dao.recoverSending()
            val saved = dao.settings() ?: SettingsEntity()
            mutableSettings.value = Settings(saved.name, saved.offline)
            initialized = true
        }
    }
    override suspend fun register(name: String) {
        val trimmed = name.trim()
        require(trimmed.isNotEmpty()) { "Enter a name" }
        network.withLock {
            check(!settings.value.offline) { "Go online to register" }
            val result = api.register(Registration(trimmed))
            check(result.name == trimmed && result.status == "registered") { "Invalid registration acknowledgement" }
            dao.saveSettings(SettingsEntity(name = trimmed, offline = false))
            mutableSettings.value = Settings(trimmed, false)
        }
        synchronize()
    }
    override suspend fun createMessage(recipient: String, text: String) {
        val user = checkNotNull(settings.value.name) { "Register first" }
        val to = recipient.trim(); val body = text.trim()
        require(to.isNotEmpty() && body.isNotEmpty()) { "Recipient and message must not be blank" }
        dao.insert(MessageEntity(messageId = UUID.randomUUID().toString(), sender = user,
            recipient = to, text = body, createdAt = Instant.now().toString(), deliveryState = "PENDING"))
        // Delivery is scheduled separately by the ViewModel: composing never waits
        // for a network timeout, and Room emits the PENDING message immediately.
    }
    override suspend fun setOffline(offline: Boolean) {
        network.withLock {
            val next = settings.value.copy(offline = offline)
            dao.saveSettings(SettingsEntity(name = next.name, offline = next.offline))
            mutableSettings.value = next
        }
        if (!offline) synchronize()
    }
    override suspend fun synchronize() = network.withLock {
        if (settings.value.offline) return@withLock
        val user = settings.value.name ?: return@withLock
        mutableError.value = null
        try {
            // Idempotent registration also restores identity on a restarted server.
            val registered = api.register(Registration(user))
            check(registered.name == user && registered.status == "registered")
        } catch (e: CancellationException) { throw e
        } catch (e: Exception) { mutableError.value = "Server unavailable: ${e.message}"; return@withLock }
        for (message in dao.pending(user)) {
            dao.updateState(message.messageId, "SENDING")
            try {
                val ack = api.send(MessageDto(message.messageId, message.sender, message.recipient, message.text, message.createdAt))
                check(ack.messageId == message.messageId && ack.status == "accepted") { "Invalid message acknowledgement" }
                dao.updateState(message.messageId, "SENT")
            } catch (e: CancellationException) {
                withContext(NonCancellable) { dao.updateState(message.messageId, "PENDING") }
                throw e
            } catch (e: Exception) {
                dao.updateState(message.messageId, "PENDING")
                mutableError.value = "Message queued: ${e.message}"
            }
        }
        try {
            api.receive(user).messages.forEachIndexed { index, message ->
                check(message.recipient == user) { "Unexpected recipient" }
                if (dao.find(message.messageId) == null) {
                    dao.insert(MessageEntity(messageId = message.messageId, sender = message.sender,
                        recipient = message.recipient, text = message.text, createdAt = message.createdAt,
                        deliveryState = "RECEIVED", incomingOrder = index.toLong()))
                }
                dao.incomingOrder(message.messageId, index.toLong())
            }
        } catch (e: CancellationException) { throw e
        } catch (e: Exception) { mutableError.value = "Could not retrieve messages: ${e.message}" }
    }
    override fun conversation(recipient: String): Flow<List<Message>> = settings.flatMapLatest { state ->
        dao.conversation(state.name ?: "", recipient.trim()).map { rows -> rows.map { it.domain() } }
    }
}
