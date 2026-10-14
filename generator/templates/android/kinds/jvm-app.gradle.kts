// {{header}}
// Kind: jvm-app (pure Kotlin/JVM application). Instantiated by apply_templates.py; edit only the deps region.
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    application
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions { jvmTarget.set(JvmTarget.JVM_17) }
}

application {
    mainClass.set("{{main_class}}")
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
