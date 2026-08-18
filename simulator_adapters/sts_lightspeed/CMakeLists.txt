cmake_minimum_required(VERSION 3.19)

project(sts_lightspeed_adapters LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

set(STS_LIGHTSPEED_ROOT "" CACHE PATH "Path to an external sts_lightspeed checkout")
if(NOT STS_LIGHTSPEED_ROOT)
    message(FATAL_ERROR "STS_LIGHTSPEED_ROOT must point to an external sts_lightspeed checkout")
endif()

cmake_path(ABSOLUTE_PATH STS_LIGHTSPEED_ROOT NORMALIZE OUTPUT_VARIABLE STS_LIGHTSPEED_ROOT_ABS)
foreach(required_path
        "${STS_LIGHTSPEED_ROOT_ABS}/include/game/GameContext.h"
        "${STS_LIGHTSPEED_ROOT_ABS}/src/game/GameContext.cpp"
        "${STS_LIGHTSPEED_ROOT_ABS}/pybind11/CMakeLists.txt"
        "${STS_LIGHTSPEED_ROOT_ABS}/json/single_include/nlohmann/json.hpp")
    if(NOT EXISTS "${required_path}")
        message(FATAL_ERROR "Incomplete sts_lightspeed checkout: missing ${required_path}")
    endif()
endforeach()

set(PYBIND11_FINDPYTHON ON)
add_subdirectory("${STS_LIGHTSPEED_ROOT_ABS}/pybind11" "${CMAKE_CURRENT_BINARY_DIR}/pybind11")

file(GLOB_RECURSE STS_LIGHTSPEED_SOURCES CONFIGURE_DEPENDS
    "${STS_LIGHTSPEED_ROOT_ABS}/src/*.cpp")

pybind11_add_module(sts_lightspeed_noncombat_adapter
    noncombat_adapter.cpp
    ${STS_LIGHTSPEED_SOURCES})

pybind11_add_module(sts_lightspeed_combat_adapter
    combat_adapter.cpp
    ${STS_LIGHTSPEED_SOURCES})

target_include_directories(sts_lightspeed_noncombat_adapter PRIVATE
    "${STS_LIGHTSPEED_ROOT_ABS}/include"
    "${STS_LIGHTSPEED_ROOT_ABS}/json/single_include")

target_include_directories(sts_lightspeed_combat_adapter PRIVATE
    "${STS_LIGHTSPEED_ROOT_ABS}/include"
    "${STS_LIGHTSPEED_ROOT_ABS}/json/single_include")

# The upstream source relies on transitive <algorithm> includes that modern
# MinGW no longer provides. Keep this compatibility shim out of the checkout.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(sts_lightspeed_noncombat_adapter PRIVATE
        -include algorithm
        -Wno-shift-count-overflow)
    target_compile_options(sts_lightspeed_combat_adapter PRIVATE
        -include algorithm
        -Wno-shift-count-overflow)
    target_link_options(sts_lightspeed_combat_adapter PRIVATE
        -static-libgcc)
    target_link_libraries(sts_lightspeed_combat_adapter PRIVATE
        "-Wl,-Bstatic"
        stdc++
        winpthread
        "-Wl,-Bdynamic"
        ucrtbase)
endif()
