-- WezTerm in omaflake's macos/research recipe: dark, JetBrains Mono Nerd Font, every window in Zellij.
-- Written once into ~/.wezterm.lua – edit it freely, omaflake does not overwrite it.
local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- The paravirtual GPU of a macOS VM has Metal but no OpenGL ("failed to create NSOpenGLPixelFormat", plan B78):
-- WebGPU draws with Metal
config.front_end = 'WebGpu'

config.font = wezterm.font 'JetBrainsMono Nerd Font'
config.font_size = 14
config.color_scheme = 'Builtin Dark'
config.window_background_opacity = 0.97
config.hide_tab_bar_if_only_one_tab = true
config.window_padding = { left = 10, right = 10, top = 8, bottom = 8 }
-- Zellij as the session: tabs, panes and detach live there ("main" is reused)
config.default_prog = { '/run/current-system/sw/bin/zellij', 'attach', '--create', 'main' }

return config
