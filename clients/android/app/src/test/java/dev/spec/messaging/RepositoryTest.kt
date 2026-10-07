package dev.spec.messaging

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import dev.spec.messaging.data.local.*
import dev.spec.messaging.data.remote.*
import dev.spec.messaging.data.repository.MessageRepositoryImpl
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.IOException
import java.time.Instant
import java.util.UUID

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class RepositoryTest {
    private lateinit var db: AppDatabase
    private lateinit var api: FakeApi
    private lateinit var repo: MessageRepositoryImpl
    private val context get() = ApplicationProvider.getApplicationContext<Context>()
    @Before fun setup() = runBlocking {
        context.deleteDatabase("test-messages.db")
        db = open()
        api = FakeApi()
        repo = MessageRepositoryImpl(db.messages(), api)
        repo.initialize(); repo.register(" Alice ")
    }
    private fun open() = Room.databaseBuilder(context, AppDatabase::class.java, "test-messages.db").build()
    @After fun cleanup() { db.close(); context.deleteDatabase("test-messages.db") }
    @Test fun offlinePersistenceAndRestartRecovery() = runBlocking {
        repo.setOffline(true)
        val calls = api.calls
        repo.createMessage(" Bob ", " Hello 🌍 ")
        repo.synchronize()
        val original = db.messages().pending("Alice").single()
        UUID.fromString(original.messageId); Instant.parse(original.createdAt)
        assertEquals("Bob", original.recipient); assertEquals("Hello 🌍", original.text)
        assertEquals(calls, api.calls)
        db.messages().updateState(original.messageId, "SENDING")
        db.close(); db = open()
        repo = MessageRepositoryImpl(db.messages(), api); repo.initialize()
        assertEquals("Alice", repo.settings.value.name)
        assertTrue(repo.settings.value.offline)
        assertEquals(original, db.messages().pending("Alice").single())
        repo.setOffline(false)
        assertEquals("SENT", db.messages().find(original.messageId)!!.deliveryState)
        assertEquals(original.messageId, api.sent.single().messageId)
    }
    @Test fun uncertainDeliveryAndMismatchRetryOriginalFields() = runBlocking {
        repo.createMessage("Bob", "hello")
        val original = db.messages().pending("Alice").single()
        api.fail = true
        repo.synchronize()
        assertEquals("PENDING", db.messages().find(original.messageId)!!.deliveryState)
        api.fail = false; api.wrongAck = true
        repo.synchronize()
        assertEquals("PENDING", db.messages().find(original.messageId)!!.deliveryState)
        api.wrongAck = false; repo.synchronize()
        assertEquals("SENT", db.messages().find(original.messageId)!!.deliveryState)
        assertEquals(1, api.sent.toSet().size)
        assertEquals(original.createdAt, api.sent.first().createdAt)
        assertEquals(1, api.accepted.size)
    }
    @Test fun queueOrderAndDuplicateServerOrder() = runBlocking {
        repo.setOffline(true)
        repo.createMessage("Bob", "first"); repo.createMessage("Bob", "second")
        val ids = db.messages().pending("Alice").map { it.messageId }
        api.inbox = listOf(
            MessageDto(UUID.randomUUID().toString(), "Bob", "Alice", "accepted first", "2030-01-01T00:00:00Z"),
            MessageDto(UUID.randomUUID().toString(), "Bob", "Alice", "accepted second", "2020-01-01T00:00:00Z")
        )
        repo.setOffline(false); repo.synchronize(); repo.synchronize()
        assertEquals(ids, api.sent.map { it.messageId })
        val messages = repo.conversation("Bob").first()
        assertEquals(4, messages.size)
        assertEquals(listOf("accepted first", "accepted second"), messages.filter { it.sender == "Bob" }.map { it.text })
        db.close(); db = open(); repo = MessageRepositoryImpl(db.messages(), api); repo.initialize(); repo.synchronize()
        assertEquals(4, repo.conversation("Bob").first().size)
    }
    @Test fun blankInputsAndRegistrationFailureDoNotPersist() = runBlocking {
        try { repo.createMessage(" ", "hello"); fail("blank recipient") } catch (_: IllegalArgumentException) {}
        try { repo.createMessage("Bob", " "); fail("blank text") } catch (_: IllegalArgumentException) {}
        assertTrue(db.messages().pending("Alice").isEmpty())
        repo.setOffline(true)
        val calls = api.calls
        try { repo.register("Bob"); fail("offline registration") } catch (_: IllegalStateException) {}
        assertEquals(calls, api.calls)
        assertEquals("Alice", repo.settings.value.name)
    }
    @Test fun aliceBobOfflineScenario() = runBlocking {
        val bobDb = Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java).build()
        try {
            val bob = MessageRepositoryImpl(bobDb.messages(), api)
            bob.initialize(); bob.register("Bob")
            repo.createMessage("Bob", "Hi Bob, I have something important to tell you"); repo.synchronize(); bob.synchronize()
            bob.createMessage("Alice", "What is it?"); bob.synchronize(); repo.synchronize()
            repo.setOffline(true); repo.createMessage("Bob", "The important message was queued while I was offline.")
            bob.setOffline(true); bob.createMessage("Alice", "I am replying while offline too.")
            assertEquals(2, api.accepted.size)
            repo.setOffline(false); repo.setOffline(true)
            bob.setOffline(false); repo.setOffline(false)
            bob.synchronize(); repo.synchronize()
            assertEquals(4, repo.conversation("Bob").first().size)
            assertEquals(4, bob.conversation("Alice").first().size)
            assertTrue(db.messages().pending("Alice").isEmpty())
            assertTrue(bobDb.messages().pending("Bob").isEmpty())
        } finally { bobDb.close() }
    }
    private class FakeApi : MessagingApi {
        var calls = 0
        var fail = false
        var wrongAck = false
        var inbox = emptyList<MessageDto>()
        val sent = mutableListOf<MessageDto>()
        val accepted = linkedMapOf<String, MessageDto>()
        override suspend fun register(user: Registration): Registered { calls++; return Registered(user.name, "registered") }
        override suspend fun send(message: MessageDto): Accepted {
            calls++; sent.add(message); accepted.putIfAbsent(message.messageId, message)
            if (fail) throw IOException("Acknowledgement lost")
            return Accepted(if (wrongAck) "wrong" else message.messageId, "accepted")
        }
        override suspend fun receive(username: String): Inbox {
            calls++
            return Inbox(inbox + accepted.values.filter { it.recipient == username })
        }
    }
}
