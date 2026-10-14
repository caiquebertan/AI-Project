// {{header}}
// Kind: jvm-lib (pure Kotlin/JVM). Instantiated by apply_templates.py; edit only the deps region.
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    `java-test-fixtures`
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions { jvmTarget.set(JvmTarget.JVM_17) }
}

val awareRepoRoot: String = providers.gradleProperty("aware.repoRoot")
    .getOrElse(rootDir.parentFile.parentFile.absolutePath)

tasks.withType<Test>().configureEach {
    systemProperty("aware.repoRoot", awareRepoRoot)
}

dependencies {
    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    // BEGIN deps
    // END deps
}
