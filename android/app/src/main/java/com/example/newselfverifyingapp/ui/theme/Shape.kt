package com.example.newselfverifyingapp.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

val Shapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(14.dp),
    large = RoundedCornerShape(18.dp),
    extraLarge = RoundedCornerShape(24.dp)
)

object AppCorners {
    val Sharp = RoundedCornerShape(4.dp)
    val Subtle = RoundedCornerShape(8.dp)
    val Component = RoundedCornerShape(14.dp) // 14 px controls from spec
    val Surface = RoundedCornerShape(18.dp)   // 18 px panels from spec
    val Modal = RoundedCornerShape(18.dp)
    val Pill = RoundedCornerShape(99.dp)      // 99 px chips from spec
}
