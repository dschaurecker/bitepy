cmake_minimum_required(VERSION 3.15)
project(bitepy LANGUAGES CXX)

find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)

find_package(CURL QUIET)
if(CURL_FOUND)
    message(STATUS "Found CURL: ${CURL_LIBRARIES}")
    set(HAS_CURL TRUE)
else()
    message(WARNING "CURL not found. Building without remote timezone database download capability.")
    set(HAS_CURL FALSE)
endif()

message(STATUS "Found Python3 Interpreter: ${Python3_EXECUTABLE}")
message(STATUS "Found Python3 Libraries: ${Python3_LIBRARIES}")
message(STATUS "Found Python3 Include Dirs: ${Python3_INCLUDE_DIRS}")

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
  get_filename_component(pybind11_SP_DIR "${pybind11_CMAKE_DIR}/../../.." ABSOLUTE)
  message(STATUS "Adding pybind11 site-packages (?) to CMAKE_PREFIX_PATH: ${pybind11_SP_DIR}")
  list(APPEND CMAKE_PREFIX_PATH "${pybind11_SP_DIR}")
endif()

find_package(pybind11 REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_OSX_DEPLOYMENT_TARGET "10.15")

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

target_include_directories(_bitepy PRIVATE
    "${PROJECT_SOURCE_DIR}/bitepy/cpp_source_submodule/bite/src"
    #"${GUROBI_INCLUDE_DIR}"
)

if(WIN32)
    target_compile_definitions(_bitepy PRIVATE HAS_REMOTE_API=0)
else()
    target_compile_definitions(_bitepy PRIVATE USE_OS_TZDB=1)
    target_compile_definitions(_bitepy PRIVATE HAS_REMOTE_API=0)
endif()

if(WIN32)
    target_link_libraries(_bitepy PRIVATE dbghelp)  # Fixed target name from _bite to _bitepy
endif()

target_link_libraries(_bitepy
    PRIVATE
        pybind11::module  # pybind11
        # gurobi_c++
        # gurobi120
)

if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
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
    target_compile_options(_bitepy PRIVATE
        /O2         # Optimization level (MSVC)
        /GL         # Whole program optimization (LTO compile part for MSVC)
    )
    target_link_options(_bitepy PRIVATE
        /LTCG       # Link-time code generation (LTO link part for MSVC)
    )
endif()

install(TARGETS _bitepy
        COMPONENT python
        LIBRARY DESTINATION bitepy  # or '.'
)