return {
	"neovim/nvim-lspconfig",
	event = { "BufReadPre", "BufNewFile" },
	dependencies = {
		"hrsh7th/cmp-nvim-lsp",
		{
			"antosha417/nvim-lsp-file-operations",
			dependencies = {
				"nvim-lua/plenary.nvim",
				"nvim-tree/nvim-tree.lua",
			},
			config = true,
		},
		{ "folke/neodev.nvim", opts = {} },
		"b0o/SchemaStore.nvim",
	},
	config = function()
		-- import cmp-nvim-lsp plugin
		local cmp_nvim_lsp = require("cmp_nvim_lsp")

		local keymap = vim.keymap -- for conciseness
		vim.api.nvim_create_autocmd("LspAttach", {
			group = vim.api.nvim_create_augroup("UserLspConfig", {}),
			callback = function(ev)
				-- Buffer local mappings.
				-- See `:help vim.lsp.*` for documentation on any of the below functions
				local opts = { buffer = ev.buf, silent = true }

				opts.desc = "Show LSP references"
				keymap.set("n", "gR", "<cmd>Telescope lsp_references<CR>", opts)
				keymap.set("n", "<leader>gr", "<cmd>Telescope lsp_references<CR>", opts)

				opts.desc = "Show LSP definitions"
				keymap.set("n", "gd", "<cmd>Telescope lsp_definitions<CR>", opts)
				keymap.set("n", "<leader>gd", "<cmd>Telescope lsp_definitions<CR>", opts)

				opts.desc = "Show LSP implementations"
				keymap.set("n", "gi", "<cmd>Telescope lsp_implementations<CR>", opts)
				keymap.set("n", "<leader>gi", "<cmd>Telescope lsp_implementations<CR>", opts)

				opts.desc = "Show LSP type definitions"
				keymap.set("n", "gt", "<cmd>Telescope lsp_type_definitions<CR>", opts)
				keymap.set("n", "<leader>gt", "<cmd>Telescope lsp_type_definitions<CR>", opts)

				opts.desc = "Show document symbols"
				keymap.set("n", "<leader>gs", "<cmd>Telescope lsp_document_symbols<CR>", opts)

				opts.desc = "See available code actions"
				keymap.set({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, opts)

				opts.desc = "Rename symbol"
				keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)

				opts.desc = "Organise imports"
				keymap.set("n", "<leader>oi", function()
					vim.lsp.buf.code_action({
						apply = true,
						context = {
							only = { "source.organizeImports" },
							diagnostics = {},
						},
					})
				end, opts)

				opts.desc = "Go to previous diagnostic"
				keymap.set("n", "[d", vim.diagnostic.goto_prev, opts)

				opts.desc = "Go to next diagnostic"
				keymap.set("n", "]d", vim.diagnostic.goto_next, opts)

				opts.desc = "Show documentation for what is under cursor"
				keymap.set("n", "K", vim.lsp.buf.hover, opts)
			end,
		})

		-- used to enable autocompletion (assign to every lsp server config)
		local capabilities = vim.tbl_deep_extend(
			"force",
			cmp_nvim_lsp.default_capabilities(),
			require("lsp-file-operations").default_capabilities()
		)

		vim.diagnostic.config({
			virtual_text = true, -- Enable inline diagnostic messages
			signs = {
				text = {
					[vim.diagnostic.severity.ERROR] = " ",
					[vim.diagnostic.severity.WARN] = " ",
					[vim.diagnostic.severity.HINT] = "󰠠 ",
					[vim.diagnostic.severity.INFO] = " ",
				},
			},
			update_in_insert = false, -- Don't show diagnostics while in insert mode
			underline = true, -- Underline the problematic code
			severity_sort = true, -- Sort by severity
			float = {
				border = "rounded",
				source = "always", -- Show source in floating window
				header = "",
				prefix = "",
			},
		})

		vim.lsp.config("*", {
			capabilities = capabilities,
		})

		vim.lsp.config("pyright", require("andreaborg.plugins.lsp.servers.pyright"))
		vim.lsp.config("gopls", require("andreaborg.plugins.lsp.servers.gopls"))
		vim.lsp.config("jdtls", require("andreaborg.plugins.lsp.servers.jdtls"))
		vim.lsp.config("yamlls", require("andreaborg.plugins.lsp.servers.yamlls"))
		vim.lsp.config("dockerls", require("andreaborg.plugins.lsp.servers.dockerls"))
		vim.lsp.config(
			"docker_compose_language_service",
			require("andreaborg.plugins.lsp.servers.docker_compose_language_service")
		)
		vim.lsp.config("lua_ls", require("andreaborg.plugins.lsp.servers.lua_ls"))
	end,
}
