-- Harpoon v1 needs Plenary's path, popup, and job modules.
vim.pack.add({ "https://github.com/nvim-lua/plenary.nvim" }, { confirm = false })

-- JSON and YAML language servers need SchemaStore's filename-to-schema catalogue.
vim.pack.add({ "https://github.com/b0o/SchemaStore.nvim" }, { confirm = false })

-- Reference server configs for languages/lsp per-language modules to adopt incrementally.
vim.pack.add({ "https://github.com/neovim/nvim-lspconfig" }, { confirm = false })

require("plugins.mason")
require("plugins.dap")
require("plugins.dap_view")
-- nvim-jdtls supplies the Java DAP bridge; native vim.lsp still starts JDT LS.
vim.pack.add({ "https://github.com/mfussenegger/nvim-jdtls" }, { confirm = false })
pcall(require, "plugins.spring_boot") -- R1: module may be removed later.
require("plugins.tmux_navigator")
require("plugins.flash")
require("plugins.treesitter")
require("plugins.marks")
require("plugins.harpoon")
require("plugins.file_explorer")
-- file_operations now lives under languages.lsp, loaded via languages.init.
require("plugins.file_search")
require("plugins.todo")
require("plugins.snippets")
require("plugins.supermaven")
