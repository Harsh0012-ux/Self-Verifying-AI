
package com.example.newselfverifyingapp.ui.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.newselfverifyingapp.data.VerificationRepositoryImpl
import com.example.newselfverifyingapp.domain.model.ExecutionEvidence
import com.example.newselfverifyingapp.domain.model.VerificationMode
import com.example.newselfverifyingapp.domain.model.VerificationSession
import com.example.newselfverifyingapp.domain.model.VerificationStatus
import com.example.newselfverifyingapp.ui.components.AppBottomNavBar
import com.example.newselfverifyingapp.ui.components.AppDestination
import com.example.newselfverifyingapp.ui.components.SessionStatusTone
import com.example.newselfverifyingapp.ui.screens.comparison.CandidateComparisonScreen
import com.example.newselfverifyingapp.ui.screens.history.SessionHistoryScreen
import com.example.newselfverifyingapp.ui.screens.home.HomeScreen
import com.example.newselfverifyingapp.ui.screens.home.RecentSessionSummary
import com.example.newselfverifyingapp.ui.screens.live.LiveVerificationScreen
import com.example.newselfverifyingapp.ui.screens.results.ResultsScreen
import com.example.newselfverifyingapp.ui.screens.verify.NewVerificationScreen
import com.example.newselfverifyingapp.ui.screens.verify.VerificationModeOption
import com.example.newselfverifyingapp.ui.theme.ColorInk
import kotlinx.coroutines.launch

sealed interface AppRoute {
    data object Home : AppRoute
    data object NewVerification : AppRoute
    data object History : AppRoute

    data class LiveVerification(
        val sessionId: String,
        val sessionNumber: Int
    ) : AppRoute

    data class CandidateComparison(
        val sessionId: String,
        val sessionNumber: Int
    ) : AppRoute

    data class Results(
        val sessionId: String,
        val sessionNumber: Int,
        val isPassed: Boolean
    ) : AppRoute
}

@Composable
fun MainNavigationContainer(modifier: Modifier = Modifier) {
    val repository = remember { VerificationRepositoryImpl() }
    val scope = rememberCoroutineScope()

    var currentRoute by remember {
        mutableStateOf<AppRoute>(AppRoute.Home)
    }

    val routeStack = remember {
        mutableStateListOf<AppRoute>(AppRoute.Home)
    }

    val history = remember {
        mutableStateListOf<VerificationSession>()
    }

    var requestError by remember {
        mutableStateOf<String?>(null)
    }

    var resultSession by remember {
        mutableStateOf<VerificationSession?>(null)
    }

    var resultLoading by remember {
        mutableStateOf(false)
    }

    val activeSession by repository.observeCurrentSession()
        .collectAsStateWithLifecycle(initialValue = null)

    fun navigateTo(route: AppRoute) {
        if (currentRoute != route) {
            currentRoute = route
            routeStack.add(route)
        }
    }

    fun popBack() {
        if (routeStack.size > 1) {
            routeStack.removeAt(routeStack.lastIndex)
            currentRoute = routeStack.lastOrNull() ?: AppRoute.Home
        } else {
            currentRoute = AppRoute.Home
        }
    }

    fun refreshHistory() {
        scope.launch {
            repository.getHistory().onSuccess { fetched ->
                history.clear()
                history.addAll(fetched)
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshHistory()
    }

    BackHandler(enabled = currentRoute != AppRoute.Home) {
        popBack()
    }

    val isTopLevelRoute =
        currentRoute is AppRoute.Home ||
                currentRoute is AppRoute.NewVerification ||
                currentRoute is AppRoute.History

    val destination = when (currentRoute) {
        is AppRoute.Home -> AppDestination.HOME
        is AppRoute.NewVerification,
        is AppRoute.LiveVerification,
        is AppRoute.CandidateComparison,
        is AppRoute.Results -> AppDestination.VERIFY
        is AppRoute.History -> AppDestination.HISTORY
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = ColorInk,
        bottomBar = {
            if (isTopLevelRoute) {
                AppBottomNavBar(
                    currentDestination = destination,
                    onNavigate = {
                        when (it) {
                            AppDestination.HOME ->
                                navigateTo(AppRoute.Home)

                            AppDestination.VERIFY ->
                                navigateTo(AppRoute.NewVerification)

                            AppDestination.HISTORY -> {
                                refreshHistory()
                                navigateTo(AppRoute.History)
                            }
                        }
                    }
                )
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(ColorInk)
                .padding(padding)
        ) {
            when (val route = currentRoute) {

                AppRoute.Home -> {
                    HomeScreen(
                        onNavigateToVerify = {
                            navigateTo(AppRoute.NewVerification)
                        },
                        onNavigateToHistory = {
                            refreshHistory()
                            navigateTo(AppRoute.History)
                        },
                        recentSessions = history.take(3).map(::summary)
                    )
                }

                AppRoute.NewVerification -> {
                    NewVerificationScreen(
                        requestError = requestError,
                        onStartVerification = {
                                question,
                                selectedMode,
                                code,
                                tests ->

                            requestError = null

                            val mode = when (selectedMode) {
                                VerificationModeOption.INTERACTIVE ->
                                    VerificationMode("interactive", "Interactive")

                                VerificationModeOption.HUMAN_EVAL ->
                                    VerificationMode("verified", "HumanEval")

                                VerificationModeOption.BASELINE ->
                                    VerificationMode("baseline", "Baseline")
                            }

                            scope.launch {
                                repository.runVerification(
                                    question,
                                    mode,
                                    code,
                                    tests
                                ).onSuccess { session ->
                                    history.removeAll {
                                        it.sessionId == session.sessionId
                                    }

                                    history.add(0, session)

                                    navigateTo(
                                        AppRoute.LiveVerification(
                                            session.sessionId,
                                            session.sessionNumber
                                        )
                                    )
                                }.onFailure {
                                    requestError = it.message
                                        ?: "Could not connect to the verification server."
                                }
                            }
                        }
                    )
                }

                AppRoute.History -> {
                    SessionHistoryScreen(
                        sessions = history.map(::summary),
                        onSessionSelected = { id ->
                            val selected = history.firstOrNull {
                                it.sessionId == id
                            }

                            if (selected != null) {
                                navigateTo(
                                    AppRoute.Results(
                                        sessionId = selected.sessionId,
                                        sessionNumber = selected.sessionNumber,
                                        isPassed = selected.status ==
                                                VerificationStatus.PASSED
                                    )
                                )
                            }
                        }
                    )
                }

                is AppRoute.LiveVerification -> {
                    val session =
                        activeSession?.takeIf {
                            it.sessionId == route.sessionId
                        } ?: history.firstOrNull {
                            it.sessionId == route.sessionId
                        }

                    LiveVerificationScreen(
                        sessionNumber = route.sessionNumber,
                        session = session,
                        onBack = {
                            popBack()
                        },
                        onViewResults = {
                            navigateTo(
                                AppRoute.Results(
                                    sessionId = route.sessionId,
                                    sessionNumber = route.sessionNumber,
                                    isPassed = session?.status ==
                                            VerificationStatus.PASSED
                                )
                            )
                        },
                        onCompareCandidates = {
                            navigateTo(
                                AppRoute.CandidateComparison(
                                    sessionId = route.sessionId,
                                    sessionNumber = route.sessionNumber
                                )
                            )
                        }
                    )

                    LaunchedEffect(session?.status) {
                        if (
                            session?.status != null &&
                            session.status != VerificationStatus.RUNNING &&
                            session.status != VerificationStatus.IDLE
                        ) {
                            refreshHistory()
                        }
                    }
                }

                is AppRoute.CandidateComparison -> {
                    val session = history.firstOrNull {
                        it.sessionId == route.sessionId
                    }

                    CandidateComparisonScreen(
                        sessionNumber = route.sessionNumber,
                        onBack = {
                            popBack()
                        },
                        onViewFullResults = {
                            navigateTo(
                                AppRoute.Results(
                                    sessionId = route.sessionId,
                                    sessionNumber = route.sessionNumber,
                                    isPassed = session?.status ==
                                            VerificationStatus.PASSED
                                )
                            )
                        }
                    )
                }

                is AppRoute.Results -> {
                    LaunchedEffect(route.sessionId) {
                        resultSession = null
                        resultLoading = true

                        repository.getSession(route.sessionId)
                            .onSuccess { fetched ->
                                resultSession = fetched
                            }

                        resultLoading = false
                    }

                    val session = resultSession?.takeIf {
                        it.sessionId == route.sessionId
                    }

                    if (resultLoading && session == null) {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "Loading session results...",
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }
                    } else if (session != null) {
                        ResultsScreen(
                            sessionNumber = session.sessionNumber,
                            isPassed = session.status == VerificationStatus.PASSED,
                            candidateCode = session.selectedCandidate?.code.orEmpty(),
                            evidence = session.evidence ?: ExecutionEvidence(),
                            tokens = session.tokensUsed ?: 0,
                            durationSeconds = session.durationSeconds ?: 0f,
                            oracleTests = session.oracleTests,
                            hiddenTestsPassed = session.hiddenTestsPassed,
                            onBack = {
                                popBack()
                            },
                            onNavigateToCandidateComparison = {
                                navigateTo(
                                    AppRoute.CandidateComparison(
                                        sessionId = route.sessionId,
                                        sessionNumber = route.sessionNumber
                                    )
                                )
                            }
                        )
                    } else {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "Could not load session results.",
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }
                    }
                }
            }
        }
    }
}

private fun summary(session: VerificationSession): RecentSessionSummary {
    val tone = when (session.status) {
        VerificationStatus.RUNNING,
        VerificationStatus.IDLE -> SessionStatusTone.RUNNING

        VerificationStatus.PASSED -> SessionStatusTone.PASSED
        VerificationStatus.EXHAUSTED -> SessionStatusTone.EXHAUSTED
        VerificationStatus.FAILED -> SessionStatusTone.FAILED
    }

    val status = when (tone) {
        SessionStatusTone.PASSED -> "Passed"
        SessionStatusTone.RUNNING -> "Running"
        SessionStatusTone.EXHAUSTED -> "Exhausted"
        SessionStatusTone.FAILED -> "Failed"
    }

    val title = (session.prompt.ifBlank {
        "${session.mode.name} session"
    }).lines().first().take(36)

    return RecentSessionSummary(
        session.sessionId,
        title,
        "#${session.sessionNumber} · ${session.mode.name} · ${
            java.text.DateFormat.getDateTimeInstance()
                .format(java.util.Date(session.timestamp))
        }",
        status,
        tone
    )
}
