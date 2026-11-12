package com.example.newselfverifyingapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import com.example.newselfverifyingapp.ui.navigation.MainNavigationContainer
import com.example.newselfverifyingapp.ui.screens.comparison.CandidateComparisonScreen
import com.example.newselfverifyingapp.ui.screens.history.SessionHistoryScreen
import com.example.newselfverifyingapp.ui.screens.home.HomeScreen
import com.example.newselfverifyingapp.ui.screens.live.LiveVerificationScreen
import com.example.newselfverifyingapp.ui.screens.results.ResultsScreen
import com.example.newselfverifyingapp.ui.screens.verify.NewVerificationScreen
import com.example.newselfverifyingapp.ui.theme.NewSelfVerifyingAppTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            NewSelfVerifyingAppTheme {
                MainNavigationContainer()
            }
        }
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun MainAppPreview() {
    NewSelfVerifyingAppTheme {
        MainNavigationContainer()
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun HomePreview() {
    NewSelfVerifyingAppTheme {
        HomeScreen(
            onNavigateToVerify = {},
            onNavigateToHistory = {}
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun NewVerificationPreview() {
    NewSelfVerifyingAppTheme {
        NewVerificationScreen(
            onStartVerification = { _, _, _, _ -> }
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun LiveVerificationPreview() {
    NewSelfVerifyingAppTheme {
        LiveVerificationScreen(
            sessionNumber = 14,
            onBack = {},
            onViewResults = {},
            onCompareCandidates = {}
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun CandidateComparisonPreview() {
    NewSelfVerifyingAppTheme {
        CandidateComparisonScreen(
            sessionNumber = 14,
            onBack = {},
            onViewFullResults = {}
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun ResultsPreview() {
    NewSelfVerifyingAppTheme {
        ResultsScreen(
            sessionNumber = 14,
            isPassed = true,
            onBack = {},
            onNavigateToCandidateComparison = {}
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF141616)
@Composable
fun HistoryPreview() {
    NewSelfVerifyingAppTheme {
        SessionHistoryScreen(
            sessions = emptyList(),
            onSessionSelected = {}
        )
    }
}
