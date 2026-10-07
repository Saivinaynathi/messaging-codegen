package dev.spec.messaging.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.*

data class MessageDto(
    @SerializedName("message_id") val messageId: String,
    val sender: String, val recipient: String, val text: String,
    @SerializedName("created_at") val createdAt: String
)
data class Registration(val name: String)
data class Registered(val name: String, val status: String)
data class Accepted(@SerializedName("message_id") val messageId: String, val status: String)
data class Inbox(val messages: List<MessageDto>)
interface MessagingApi {
    @POST("users/register") suspend fun register(@Body user: Registration): Registered
    @POST("messages") suspend fun send(@Body message: MessageDto): Accepted
    @GET("messages/{username}") suspend fun receive(@Path("username") username: String): Inbox
}
