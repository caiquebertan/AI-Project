// {{header}}
// Kind: android-app (the Android application). Instantiated by apply_templates.py; edit only the deps region.
// Its src/main/AndroidManifest.xml and res/xml/network_security_config.xml are template-owned.
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

val awareRepoRoot: String = providers.gradleProperty("aware.repoRoot")
    .getOrElse(rootDir.parentFile.parentFile.absolutePath)
val awareServerUrl: String = providers.gradleProperty("aware.serverUrl").get()

android {
    namespace = "{{namespace}}"
    compileSdk = libs.versions.compileSdk.get().toInt()
    defaultConfig {
        applicationId = "app.aware.android"
        minSdk = libs.versions.minSdk.get().toInt()
        targetSdk = libs.versions.targetSdk.get().toInt()
        versionCode = 1
        versionName = "{{spec_version}}"
        buildConfigField("String", "SERVER_BASE_URL", "\"$awareServerUrl\"")
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions {
        unitTests.isIncludeAndroidResources = true
    }
}

kotlin {
    compilerOptions { jvmTarget.set(JvmTarget.JVM_17) }
}

tasks.withType<Test>().configureEach {
    systemProperty("aware.repoRoot", awareRepoRoot)
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    testImplementation(libs.junit)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.core)
    testImplementation(libs.androidx.test.ext.junit)
    // BEGIN deps
    // END deps
}
