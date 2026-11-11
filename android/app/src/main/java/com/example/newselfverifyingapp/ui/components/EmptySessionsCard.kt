package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.ColorIvory
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.ColorPanel
import com.example.newselfverifyingapp.ui.theme.Typography

/**
 * Empty state container matching the Ember Ledger design specification.
 */
@Composable
fun EmptySessionsCard(
    modifier: Modifier = Modifier,
    title: String = "No sessions yet",
    subtitle: String = "Run your first verification."
) {
    AppSurfaceCard(
        modifier = modifier.fillMaxWidth(),
        shape = AppCorners.Surface,
        backgroundColor = ColorPanel,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 32.dp, horizontal = 20.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = title,
                style = Typography.titleMedium.copy(
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                ),
                color = ColorIvory
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = subtitle,
                style = Typography.bodyMedium,
                color = ColorMuted
            )
        }
    }
}

