// {{header}}
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "aware-android"

// Every directory up to two levels deep that has a build.gradle.kts is a module, so a module
// list that changes in the spec needs no edit here (generator design §1.3).
val skippedDirs = setOf("build", "gradle", "buildSrc")

fun moduleCandidates(dir: java.io.File): List<java.io.File> =
    dir.listFiles().orEmpty().filter { it.isDirectory && !it.name.startsWith(".") && it.name !in skippedDirs }

moduleCandidates(rootDir)
    .flatMap { top -> listOf(top) + moduleCandidates(top) }
    .filter { it.resolve("build.gradle.kts").isFile }
    .map { ":" + it.relativeTo(rootDir).invariantSeparatorsPath.replace('/', ':') }
    .sorted()
    .forEach { include(it) }
