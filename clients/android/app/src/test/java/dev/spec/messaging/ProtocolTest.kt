package dev.spec.messaging

import com.google.gson.Gson
import dev.spec.messaging.data.remote.*
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Test
import org.junit.Assert.*
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ProtocolTest {
    @Test fun endpointsAndJsonMatchSpecification() = runBlocking {
        val server = MockWebServer(); server.start()
        try {
            val api = Retrofit.Builder().baseUrl(server.url("/"))
                .addConverterFactory(GsonConverterFactory.create()).build().create(MessagingApi::class.java)
            server.enqueue(MockResponse().setBody("""{"name":"Alice","status":"registered"}"""))
            api.register(Registration("Alice"))
            assertEquals("/users/register", server.takeRequest().path)
            server.enqueue(MockResponse().setBody("""{"message_id":"id","status":"accepted"}"""))
            api.send(MessageDto("id", "Alice", "Bob", "hello", "2026-10-05T20:00:00Z"))
            val request = server.takeRequest()
            assertEquals("POST", request.method); assertEquals("/messages", request.path)
            val json = Gson().fromJson(request.body.readUtf8(), Map::class.java)
            assertEquals(setOf("message_id", "sender", "recipient", "text", "created_at"), json.keys)
            server.enqueue(MockResponse().setBody("""{"messages":[]}"""))
            assertTrue(api.receive("Bob Smith").messages.isEmpty())
            assertEquals("/messages/Bob%20Smith", server.takeRequest().path)
        } finally { server.shutdown() }
    }
}
