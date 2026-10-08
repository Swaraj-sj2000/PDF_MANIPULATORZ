cmake_minimum_required(VERSION 3.16)
project(manual_notes_compiler VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(manual-notes-compiler
    src/main.cpp
)

target_link_libraries(manual-notes-compiler PRIVATE Qt5::Widgets)

install(TARGETS manual-notes-compiler RUNTIME DESTINATION bin)
