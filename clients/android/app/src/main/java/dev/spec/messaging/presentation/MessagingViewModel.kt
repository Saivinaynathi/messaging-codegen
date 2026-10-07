package dev.spec.messaging.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dev.spec.messaging.domain.*
import javax.inject.Inject
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

@HiltViewModel
class MessagingViewModel @Inject constructor(private val repository: MessageRepository) : ViewModel() {
    val settings = repository.settings
    val networkError = repository.error
    private val mutableError = MutableStateFlow<String?>(null)
    val error = mutableError.asStateFlow()
    private val mutableReady = MutableStateFlow(false)
    val ready = mutableReady.asStateFlow()
    private val recipient = MutableStateFlow("")
    val messages = recipient.flatMapLatest(repository::conversation)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    init {
        action {
            repository.initialize()
            mutableReady.value = true
            while (isActive) {
                repository.synchronize()
                delay(5000)
            }
        }
    }
    fun selectRecipient(value: String) { recipient.value = value }
    fun register(name: String) = action { repository.register(name) }
    fun send(to: String, text: String, onStored: () -> Unit) = action {
        repository.createMessage(to, text)
        onStored()
        action { repository.synchronize() }
    }
    fun offline(value: Boolean) = action { repository.setOffline(value) }
    fun sync() = action { repository.synchronize() }
    private fun action(block: suspend CoroutineScope.() -> Unit) = viewModelScope.launch {
        mutableError.value = null
        try { block() } catch (e: CancellationException) { throw e }
        catch (e: Exception) { mutableError.value = e.message ?: "Operation failed" }
    }
}
