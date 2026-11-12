package com.example.newselfverifyingapp.ui.screens.verify

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.ui.components.AppPanelCard
import com.example.newselfverifyingapp.ui.components.AppSurfaceCard
import com.example.newselfverifyingapp.ui.components.EmberCtaButton
import com.example.newselfverifyingapp.ui.components.EmberDashedCard
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorInk
import com.example.newselfverifyingapp.ui.theme.ColorIvory
import com.example.newselfverifyingapp.ui.theme.ColorLine
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.ColorPanel
import com.example.newselfverifyingapp.ui.theme.EmberTypography
import com.example.newselfverifyingapp.ui.theme.Typography

enum class VerificationModeOption(val title: String) {
    INTERACTIVE("Interactive"),
    HUMAN_EVAL("HumanEval"),
    BASELINE("Baseline")
}

/**
 * Authoritative reproduction of screen 2 New verification.png.
 */
@Composable
fun NewVerificationScreen(
    onStartVerification: (question: String, mode: VerificationModeOption, code: String, tests: List<String>) -> Unit,
    modifier: Modifier = Modifier,
    requestError: String? = null
) {
    var selectedMode by remember { mutableStateOf(VerificationModeOption.INTERACTIVE) }
    var questionText by remember {
        mutableStateOf("Write is_palindrome(s). Ignore case and punctuation.")
    }
    var isStartingCodeExpanded by remember { mutableStateOf(false) }
    var startingCodeText by remember { mutableStateOf("def is_palindrome(s: str) -> bool:\n    pass") }
    var testAssertionsText by remember {
        mutableStateOf("assert is_palindrome(\"Racecar\")\nassert not is_palindrome(\"hello\")")
    }
    var pendingNoticeMessage by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(ColorInk)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {
        // 1. Header
        Text(
            text = "NEW VERIFICATION",
            style = EmberTypography.Overline
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = "What should it solve?",
            style = EmberTypography.ScreenTitle
        )

        Spacer(modifier = Modifier.height(20.dp))

        // 2. Segmented Mode Selector
        ModeSegmentedControl(
            selectedMode = selectedMode,
            onModeSelected = { selectedMode = it }
        )

        Spacer(modifier = Modifier.height(24.dp))

        // 3. Question Required Input
        Text(
            text = "QUESTION · REQUIRED",
            style = EmberTypography.Overline
        )

        Spacer(modifier = Modifier.height(10.dp))

        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
        ) {
            BasicTextField(
                value = questionText,
                onValueChange = { questionText = it },
                textStyle = Typography.bodyLarge.copy(
                    fontSize = 15.sp,
                    lineHeight = 22.sp,
                    color = ColorIvory
                ),
                cursorBrush = SolidColor(ColorBronze),
                modifier = Modifier.fillMaxWidth()
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 4. Starting Code (Optional, Expandable)
        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            onClick = { isStartingCodeExpanded = !isStartingCodeExpanded },
            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp, vertical = 14.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Starting code · optional",
                        style = Typography.titleMedium.copy(fontSize = 14.sp),
                        color = ColorIvory
                    )
                    Text(
                        text = if (isStartingCodeExpanded) "−" else "+",
                        style = Typography.titleMedium.copy(fontSize = 18.sp),
                        color = ColorMuted
                    )
                }

                AnimatedVisibility(visible = isStartingCodeExpanded) {
                    Column {
                        Spacer(modifier = Modifier.height(12.dp))
                        AppPanelCard(
                            modifier = Modifier.fillMaxWidth(),
                            contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp)
                        ) {
                            BasicTextField(
                                value = startingCodeText,
                                onValueChange = { startingCodeText = it },
                                textStyle = EmberTypography.MonospaceCode.copy(fontSize = 13.sp),
                                cursorBrush = SolidColor(ColorBronze),
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 5. Your Tests Section
        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Your tests · optional",
                        style = Typography.titleMedium.copy(fontSize = 14.sp),
                        color = ColorIvory
                    )

                    Box(
                        modifier = Modifier
                            .border(1.dp, ColorBronze, AppCorners.Pill)
                            .padding(horizontal = 10.dp, vertical = 3.dp)
                    ) {
                        Text(
                            text = "Authoritative",
                            style = EmberTypography.MonospaceMeta.copy(fontSize = 11.sp),
                            color = ColorBronze
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                AppPanelCard(
                    modifier = Modifier.fillMaxWidth(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp)
                ) {
                    BasicTextField(
                        value = testAssertionsText,
                        onValueChange = { testAssertionsText = it },
                        textStyle = EmberTypography.MonospaceCode.copy(
                            fontSize = 13.sp,
                            lineHeight = 19.sp,
                            color = ColorIvory
                        ),
                        cursorBrush = SolidColor(ColorBronze),
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "+ Add assertion",
                    style = Typography.labelMedium.copy(
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        color = ColorBronze
                    ),
                    modifier = Modifier.clickable {
                        testAssertionsText += "\nassert is_palindrome(\"\")"
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 6. Dashed Helper Notice Card
        EmberDashedCard(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "No tests? The model writes them, pooled across candidates. Shown as weaker evidence.",
                style = Typography.bodySmall.copy(fontSize = 12.sp, lineHeight = 17.sp),
                color = ColorMuted
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        // 7. Configuration Parameters Chips
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ConfigParamChip(label = "3 candidates")
            ConfigParamChip(label = "≤2 repairs")
            ConfigParamChip(label = "5 s sandbox")

            Spacer(modifier = Modifier.weight(1f))

            Text(
                text = "server config",
                style = Typography.bodySmall.copy(fontSize = 11.sp),
                color = ColorMuted
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Pending notification banner if clicked
        if (requestError != null || pendingNoticeMessage != null) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF2B1F16), shape = AppCorners.Component)
                    .border(1.dp, ColorBronze.copy(alpha = 0.5f), shape = AppCorners.Component)
                    .padding(12.dp)
            ) {
                Text(
                    text = requestError ?: pendingNoticeMessage.orEmpty(),
                    style = Typography.bodySmall,
                    color = ColorBronze
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
        }

        // 8. Main Action Button: Start verification
        EmberCtaButton(
            text = "Start verification",
            onClick = {
                onStartVerification(questionText, selectedMode, startingCodeText, testAssertionsText.lines().map { it.trim() }.filter { it.isNotBlank() })
            }
        )

        Spacer(modifier = Modifier.height(28.dp))
    }
}

@Composable
private fun ModeSegmentedControl(
    selectedMode: VerificationModeOption,
    onModeSelected: (VerificationModeOption) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(ColorPanel, shape = AppCorners.Component)
            .border(1.dp, ColorLine, AppCorners.Component)
            .padding(4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        VerificationModeOption.entries.forEach { mode ->
            val isSelected = mode == selectedMode
            Box(
                modifier = Modifier
                    .weight(1f)
                    .background(
                        color = if (isSelected) ColorBronze else Color.Transparent,
                        shape = AppCorners.Component
                    )
                    .clickable { onModeSelected(mode) }
                    .padding(vertical = 10.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = mode.title,
                    style = Typography.labelLarge.copy(
                        fontSize = 13.sp,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal
                    ),
                    color = if (isSelected) ColorInk else ColorMuted
                )
            }
        }
    }
}

@Composable
private fun ConfigParamChip(label: String) {
    Box(
        modifier = Modifier
            .border(1.dp, ColorLine, AppCorners.Pill)
            .padding(horizontal = 10.dp, vertical = 4.dp)
    ) {
        Text(
            text = label,
            style = Typography.labelSmall.copy(fontSize = 11.sp),
            color = ColorIvory
        )
    }
}

