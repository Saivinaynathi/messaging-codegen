package dev.spec.messaging.di

import android.content.Context
import androidx.room.Room
import dagger.*
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import dev.spec.messaging.BuildConfig
import dev.spec.messaging.data.local.*
import dev.spec.messaging.data.remote.MessagingApi
import dev.spec.messaging.data.repository.MessageRepositoryImpl
import dev.spec.messaging.domain.MessageRepository
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton fun database(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "messaging.db").build()
    @Provides fun dao(database: AppDatabase): MessageDao = database.messages()
    @Provides @Singleton fun api(): MessagingApi = Retrofit.Builder()
        .baseUrl(BuildConfig.SERVER_URL)
        .client(OkHttpClient.Builder().callTimeout(10, TimeUnit.SECONDS).build())
        .addConverterFactory(GsonConverterFactory.create()).build().create(MessagingApi::class.java)
    @Provides @Singleton fun repository(impl: MessageRepositoryImpl): MessageRepository = impl
}
