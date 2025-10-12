cmake_minimum_required(VERSION 3.15)
project(bitepy LANGUAGES CXX)

# Find Python 3 interpreter and development components
find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)

# Find CURL (required for timezone database downloads)
# Make CURL optional to allow builds without remote timezone download capability
find_package(CURL QUIET)
if(CURL_FOUND)
    message(STATUS "Found CURL: ${CURL_LIBRARIES}")
    set(HAS_CURL TRUE)
else()
    message(WARNING "CURL not found. Building without remote timezone database download capability.")
    set(HAS_CURL FALSE)
endif()

message(STATUS "Found Python3 Interpreter: ${Python3_EXECUTABLE}")
# Note: These might be empty if CMake uses imported targets primarily
message(STATUS "Found Python3 Libraries: ${Python3_LIBRARIES}")
message(STATUS "Found Python3 Include Dirs: ${Python3_INCLUDE_DIRS}")

# Get the pybind11 CMake directory using the Python interpreter
# This ensures we find the pybind11 associated with the Python being used for the build
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
  OUTPUT_VARIABLE pybind11_CMAKE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET # Optionally hide errors if pybind11 command fails
  RESULT_VARIABLE pybind11_CMD_RESULT
)

if(NOT pybind11_CMD_RESULT EQUAL 0 OR NOT IS_DIRECTORY "${pybind11_CMAKE_DIR}")
  message(FATAL_ERROR "pybind11 CMake directory not found using 'python -m pybind11 --cmakedir'. "
                      "Ensure pybind11 is installed in the build environment (check pyproject.toml).")
else()
  message(STATUS "Found pybind11 CMake directory: ${pybind11_CMAKE_DIR}")
  # Add the found directory to CMake's search path for modules
  # list(APPEND CMAKE_MODULE_PATH "${pybind11_CMAKE_DIR}")
  # Often, pointing CMAKE_PREFIX_PATH to the site-packages root works better for find_package config mode:
  # Determine site-packages based on the found pybind11 CMake dir (may need adjustment)
  get_filename_component(pybind11_SP_DIR "${pybind11_CMAKE_DIR}/../../.." ABSOLUTE)
  message(STATUS "Adding pybind11 site-packages (?) to CMAKE_PREFIX_PATH: ${pybind11_SP_DIR}")
  list(APPEND CMAKE_PREFIX_PATH "${pybind11_SP_DIR}")
  # Alternatively, explicitly set pybind11_DIR (less common now but sometimes works)
  # set(pybind11_DIR ${pybind11_CMAKE_DIR})
endif()

# --- Find Python and pybind11 ---
# Request both the interpreter and development components.
find_package(pybind11 REQUIRED)

# --- Set your desired C++ standard and compile options ---
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)


# --- Add your library/executable, in this case a Python extension module ---
# We'll call the library "_bitepy" so that scikit-build produces _bitepy.<ext> 
pybind11_add_module(_bitepy
    bitepy/_bitepy.cpp
    bitepy/cpp_source_submodule/bite/src/Simulation.cpp
    bitepy/cpp_source_submodule/bite/src/GeneralStageProblem.cpp
    bitepy/cpp_source_submodule/bite/src/LimitOrderQueue.cpp
    bitepy/cpp_source_submodule/bite/src/LimitOrder.cpp
    bitepy/cpp_source_submodule/bite/src/MarketOrder.cpp
    bitepy/cpp_source_submodule/bite/src/LogLimitOrder.cpp
    bitepy/cpp_source_submodule/bite/src/ExecMarketOrder.cpp
    bitepy/cpp_source_submodule/bite/src/LogAcceptedOrder.cpp
    bitepy/cpp_source_submodule/bite/src/OrderBook.cpp
    bitepy/cpp_source_submodule/bite/src/ForeLogOrder.cpp
    bitepy/cpp_source_submodule/bite/src/SimulationParameters.cpp
    bitepy/cpp_source_submodule/bite/src/Util.cpp
    bitepy/cpp_source_submodule/bite/src/MILPStats.cpp
    bitepy/cpp_source_submodule/bite/src/BalancingOrder.cpp
    bitepy/cpp_source_submodule/bite/src/OrderQueue.cpp
    bitepy/cpp_source_submodule/bite/src/tz.cpp
)

set_target_properties(_bitepy
    PROPERTIES
        CXX_STANDARD 20
        CXX_STANDARD_REQUIRED YES
        CXX_EXTENSIONS NO
)

# OLD
# --- Include directories ---
# target_include_directories(_bitepy
#     PRIVATE
#         ${PROJECT_SOURCE_DIR}/_bitepy/include
#         /opt/homebrew/include
#         /Library/gurobi1200/macos_universal2/include
# )

# target_link_directories(_bitepy
#     PRIVATE
#         /Library/gurobi1200/macos_universal2/lib
# )

# NEW
# # Attempt to find Gurobi includes
# find_path(GUROBI_INCLUDE_DIR
#     NAMES gurobi_c++.h
#     HINTS
#         /Library/gurobi1200/macos_universal2/include
#         # You can add more guess paths or rely on the user's environment
# )

# # Attempt to find Gurobi libraries
# find_library(GUROBI_LIB
#     NAMES gurobi_c++
#     HINTS
#         /Library/gurobi1200/macos_universal2/lib
#         # Again, you can add more guess paths here
# )

# # If either isn't found, you can issue an error or warning
# if (NOT GUROBI_INCLUDE_DIR OR NOT GUROBI_LIB)
#     message(FATAL_ERROR "Could NOT find Gurobi. Please specify GUROBI_INCLUDE_DIR and GUROBI_LIB.")
# endif()

# Then add them to your target:
target_include_directories(_bitepy PRIVATE
    "${PROJECT_SOURCE_DIR}/bitepy/cpp_source_submodule/bite/src"
    #"${GUROBI_INCLUDE_DIR}"
)

#target_link_libraries(_bitepy PRIVATE "${GUROBI_LIB}")

# Set up compiler definitions and link libraries based on available dependencies
# Use OS timezone database on Unix-like systems (Linux, macOS), but not on Windows
if(WIN32)
    # On Windows, use embedded timezone database (USE_OS_TZDB=0 is default)
    # and disable remote API
    target_compile_definitions(_bitepy PRIVATE HAS_REMOTE_API=0)
else()
    # On Unix-like systems, use OS timezone database
    target_compile_definitions(_bitepy PRIVATE USE_OS_TZDB=1)
    # When using OS timezone database, HAS_REMOTE_API must be 0 (they cannot be used together)
    target_compile_definitions(_bitepy PRIVATE HAS_REMOTE_API=0)
endif()

target_link_libraries(_bitepy
    PRIVATE
        pybind11::module  # pybind11
        # gurobi_c++
        # gurobi120
)

if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # --- Common Flags for GCC and Clang based compilers ---
    target_compile_options(_bitepy PRIVATE
        -O3          # Optimization level
        -funroll-loops # Loop unrolling optimization
        -flto        # Link-time optimization (compile part)
        -std=c++20   # Set C++ standard
    )
    target_link_options(_bitepy PRIVATE
        -flto        # Link-time optimization (link part)
    )

elseif (CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    # --- MSVC Flags ---
    target_compile_options(_bitepy PRIVATE
        /O2         # Optimization level (MSVC)
        /GL         # Whole program optimization (LTO compile part for MSVC)
        # /arch:AVX2  # Be careful with specific instruction sets, ensure compatibility if uncommented
    )
    target_link_options(_bitepy PRIVATE
        /LTCG       # Link-time code generation (LTO link part for MSVC)
    )
endif()

# Tell CMake to name the target _bitepy.<so/pyd>: (does not work)
# set_target_properties(_bitepy PROPERTIES
#     PREFIX "${Python3_MODULE_PREFIX}"
#     SUFFIX "${Python3_MODULE_EXTENSION}"
# )

install(TARGETS _bitepy
        COMPONENT python
        LIBRARY DESTINATION bitepy  # or '.'
)

#######
# BACKUP
#######

# cmake_minimum_required(VERSION 3.15)
# project(bite LANGUAGES CXX)

# find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)
# find_package(pybind11 REQUIRED)

# set(CMAKE_CXX_STANDARD 17)
# set(CMAKE_CXX_STANDARD_REQUIRED ON)
# set(CMAKE_CXX_EXTENSIONS OFF)

# # --- Determine the correct precompiled simulation library ---
# if(WIN32)
#     if(Python3_VERSION_MAJOR EQUAL 3 AND Python3_VERSION_MINOR GREATER_EQUAL 8 AND Python3_VERSION_MINOR LESS_EQUAL 13)
#         if(Python3_VERSION_MINOR EQUAL 8)
#             set(CP_TAG "3.8")
#         elseif(Python3_VERSION_MINOR EQUAL 9)
#             set(CP_TAG "3.9")
#         elseif(Python3_VERSION_MINOR EQUAL 10)
#             set(CP_TAG "3.10")
#         elseif(Python3_VERSION_MINOR EQUAL 11)
#             set(CP_TAG "3.11")
#         elseif(Python3_VERSION_MINOR EQUAL 12)
#             set(CP_TAG "3.12")
#         elseif(Python3_VERSION_MINOR EQUAL 13)
#             set(CP_TAG "3.13")
#         endif()
#         set(SIM_LIB_PATH "${PROJECT_SOURCE_DIR}/libs/_bitepy_win_py${CP_TAG}.dll")
#         set(SIM_IMPLIB_PATH "${PROJECT_SOURCE_DIR}/libs/_bitepy_win_py${CP_TAG}.lib")
#     else()
#         message(FATAL_ERROR "Unsupported Python version on Windows")
#     endif()
# elseif(APPLE)
#     if(Python3_VERSION_MAJOR EQUAL 3 AND Python3_VERSION_MINOR GREATER_EQUAL 8 AND Python3_VERSION_MINOR LESS_EQUAL 13)
#         if(Python3_VERSION_MINOR EQUAL 8)
#             set(CP_TAG "3.8")
#         elseif(Python3_VERSION_MINOR EQUAL 9)
#             set(CP_TAG "3.9")
#         elseif(Python3_VERSION_MINOR EQUAL 10)
#             set(CP_TAG "3.10")
#         elseif(Python3_VERSION_MINOR EQUAL 11)
#             set(CP_TAG "3.11")
#         elseif(Python3_VERSION_MINOR EQUAL 12)
#             set(CP_TAG "3.12")
#         elseif(Python3_VERSION_MINOR EQUAL 13)
#             set(CP_TAG "3.13")
#         endif()
#         set(SIM_LIB_PATH "${PROJECT_SOURCE_DIR}/libs/_bitepy_mac_py${CP_TAG}.dylib")
#     else()
#         message(FATAL_ERROR "Unsupported Python version on macOS")
#     endif()
# else()  # Assume Linux
#     if(Python3_VERSION_MAJOR EQUAL 3 AND Python3_VERSION_MINOR GREATER_EQUAL 8 AND Python3_VERSION_MINOR LESS_EQUAL 13)
#         if(Python3_VERSION_MINOR EQUAL 8)
#             set(CP_TAG "3.8")
#         elseif(Python3_VERSION_MINOR EQUAL 9)
#             set(CP_TAG "3.9")
#         elseif(Python3_VERSION_MINOR EQUAL 10)
#             set(CP_TAG "3.10")
#         elseif(Python3_VERSION_MINOR EQUAL 11)
#             set(CP_TAG "3.11")
#         elseif(Python3_VERSION_MINOR EQUAL 12)
#             set(CP_TAG "3.12")
#         elseif(Python3_VERSION_MINOR EQUAL 13)
#             set(CP_TAG "3.13")
#         endif()
#         set(SIM_LIB_PATH "${PROJECT_SOURCE_DIR}/libs/_bitepy_linux_py${CP_TAG}.so")
#     else()
#         message(FATAL_ERROR "Unsupported Python version on Linux")
#     endif()
# endif()

# # Declare an imported target for your precompiled simulation library.
# add_library(bite_lib SHARED IMPORTED)
# set_target_properties(bite_lib PROPERTIES
#     IMPORTED_LOCATION "${SIM_LIB_PATH}"
#     IMPORTED_IMPLIB "${SIM_IMPLIB_PATH}"
# )

# # Determine a short platform name.
# if(WIN32)
#     set(PLATFORM "win")
# elseif(APPLE)
#     set(PLATFORM "mac")
# elseif(UNIX)
#     set(PLATFORM "linux")
# else()
#     set(PLATFORM "unknown")
# endif()

# # --- Build the Python wrapper ---
# add_library(_bitepy SHARED
#     bite/_bitepy.cpp
# )

# set_target_properties(_bitepy
#     PROPERTIES
#         CXX_STANDARD 17
#         CXX_STANDARD_REQUIRED YES
#         CXX_EXTENSIONS NO
# )

# target_include_directories(_bitepy PRIVATE
#     "${PROJECT_SOURCE_DIR}/include"
# )

# # Remove the default prefix to avoid a "lib" being added on some systems
# set_target_properties(_bitepy PROPERTIES PREFIX "")

# # Set the output name to include the system and Python version.
# # Python3_VERSION is provided by the Python3 package.
# string(REGEX MATCH "^[0-9]+\\.[0-9]+" PYTHON3_VERSION_SHORT ${Python3_VERSION})
# set_target_properties(_bitepy PROPERTIES OUTPUT_NAME "_bitepy_${PLATFORM}_py${PYTHON3_VERSION_SHORT}")

# # Link the Python module with the precompiled simulation library.
# target_link_libraries(_bitepy
#     PRIVATE
#         pybind11::module
#         bite_lib
# )

# # --- Compiler-specific options ---
# if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
#     target_compile_options(_bitepy PRIVATE
#         -O3
#         -march=native
#         -funroll-loops
#         -flto
#         -std=c++17
#     )
#     target_link_options(_bitepy PRIVATE
#         -flto
#     )
# elseif (CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
#     target_compile_options(_bitepy PRIVATE
#         /O2
#         /GL
#         /arch:AVX2 
#     )
#     target_link_options(_bitepy PRIVATE
#         /LTCG
#     )
# endif()

# install(TARGETS _bitepy
#         COMPONENT python
#         LIBRARY DESTINATION bite
# )
