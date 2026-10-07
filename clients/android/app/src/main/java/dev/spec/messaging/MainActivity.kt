package dev.spec.messaging

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dagger.hilt.android.AndroidEntryPoint
import dev.spec.messaging.presentation.MessagingViewModel

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val model: MessagingViewModel by viewModels()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { MessagingScreen(model) } }
    }
}
@Composable
private fun MessagingScreen(model: MessagingViewModel) {
    val settings by model.settings.collectAsStateWithLifecycle()
    val ready by model.ready.collectAsStateWithLifecycle()
    val error by model.error.collectAsStateWithLifecycle()
    val networkError by model.networkError.collectAsStateWithLifecycle()
    val messages by model.messages.collectAsStateWithLifecycle()
    var name by rememberSaveable { mutableStateOf("") }
    var recipient by rememberSaveable { mutableStateOf("") }
    var text by rememberSaveable { mutableStateOf("") }
    var storing by remember { mutableStateOf(false) }
    LaunchedEffect(recipient) { model.selectRecipient(recipient) }
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(Modifier.safeDrawingPadding().imePadding().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Messaging Demo", style = MaterialTheme.typography.headlineMedium)
            if (!ready) { CircularProgressIndicator(); return@Column }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(if (settings.offline) "OFFLINE" else "ONLINE", Modifier.weight(1f))
                Text("Offline mode")
                Switch(checked = settings.offline, onCheckedChange = model::offline)
            }
            (error ?: networkError)?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            if (settings.name == null) {
                OutlinedTextField(name, { name = it }, label = { Text("Your name") }, singleLine = true)
                Button(onClick = { model.register(name) }, enabled = name.trim().isNotEmpty() && !settings.offline) { Text("Continue") }
                if (settings.offline) Text("Go online to register your name.")
            } else {
                Text("Signed in as ${settings.name}")
                OutlinedTextField(recipient, { recipient = it }, label = { Text("Recipient / conversation") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                LazyColumn(Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(messages, key = { it.messageId }) { message ->
                        val outgoing = message.sender == settings.name
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = if (outgoing) Arrangement.End else Arrangement.Start) {
                            Card(colors = CardDefaults.cardColors(containerColor = if (outgoing) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.secondaryContainer), modifier = Modifier.fillMaxWidth(0.85f)) {
                                Column(Modifier.padding(12.dp)) {
                                    Text("${message.sender} → ${message.recipient}")
                                    Text(message.text)
                                    Text(message.createdAt, style = MaterialTheme.typography.labelSmall)
                                    if (outgoing) Text(message.deliveryState.name, style = MaterialTheme.typography.labelMedium)
                                }
                            }
                        }
                    }
                }
                OutlinedTextField(text, { text = it }, label = { Text("Message") }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(enabled = !storing && recipient.trim().isNotEmpty() && text.trim().isNotEmpty(), onClick = {
                        storing = true
                        val job = model.send(recipient, text) { text = "" }
                        job.invokeOnCompletion { storing = false }
                    }) { Text("Send") }
                    OutlinedButton(onClick = model::sync, enabled = !settings.offline) { Text("Sync / retry") }
                }
            }
        }
    }
}
