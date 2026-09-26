local function format_java(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local command = { "palantir-java-format", "--palantir", "--assume-filename", vim.api.nvim_buf_get_name(bufnr), "-" }
	local after = vim.fn.systemlist(command, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("Palantir could not format this Java file", vim.log.levels.ERROR)
		return
	end

	require("languages.lsp.format").apply_diff(bufnr, after)
end

require("languages.lsp.format").format_on_save("java", format_java)

local jdtls_execute_client_command_patched = false

vim.lsp.config("jdtls", {
	cmd = function(dispatchers, config)
		-- Eclipse stores project metadata under -data; hash the full root path (not just its
		-- basename) so same-named projects under different parents get separate workspaces.
		-- Root-less files (no project markers found) get their own workspace keyed off their
		-- own path instead of sharing one nil/v:null workspace.
		local workspace_key = config.root_dir and vim.fn.sha256(config.root_dir)
			or vim.fn.sha256(vim.api.nvim_buf_get_name(0))
		local workspace = vim.fn.stdpath("cache") .. "/jdtls/" .. workspace_key
		return vim.lsp.rpc.start({ "jdtls", "-data", workspace }, dispatchers)
	end,
	-- Prefer a nested Java project over the enclosing repository's Git root.
	root_markers = { { "mvnw", "gradlew", "settings.gradle", "settings.gradle.kts", "pom.xml", "build.gradle", "build.gradle.kts", "build.xml" }, ".git" },
	before_init = function(params)
		-- The extensions table is cached and shared across all jdtls instances; copy it so
		-- appending the debug-adapter jars below never mutates the shared cache.
		local bundles = vim.deepcopy(require("spring_boot").java_extensions())
		local debug_jars = vim.fn.glob(
			vim.fn.stdpath("data") .. "/mason/share/java-debug-adapter/com.microsoft.java.debug.plugin-*.jar",
			false,
			true
		)
		vim.list_extend(bundles, debug_jars)
		params.initializationOptions = { bundles = bundles }
	end,
	settings = {
		java = {
			completion = { importOrder = { "java", "javax", "org", "com" } },
			format = { enabled = false },
			-- referencesCodeLens = { enabled = true }, -- disabled per plan decision
			-- inlayHints: jdt.ls v1.61.0 (the only version Mason's registry can install -- it is
			-- both the latest git tag and the only version whose snapshot download URL resolves)
			-- never wires ServerCapabilities.inlayHintProvider (verified via jar bytecode
			-- inspection); settings kept commented for when a fixed build is available.
			-- inlayHints = {
			-- 	parameterNames = { enabled = "all", suppressWhenSameNameNumbered = true },
			-- 	variableTypes = { enabled = true },
			-- 	parameterTypes = { enabled = true },
			-- 	formatParameters = { enabled = true },
			-- },
			saveActions = { organizeImports = require("config").AUTO_FORMAT },
			sources = { organizeImports = { starThreshold = 999, staticStarThreshold = 999 } },
		},
	},
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		require("jdtls").setup_dap()

		-- nvim-jdtls's workspace/executeClientCommand handler returns a bare
		-- nil for client commands with no return value; Neovim's RPC layer
		-- rejects that ("either a result or an error must be sent"). Coerce
		-- nil to vim.NIL so void commands still get a valid JSON-RPC null.
		if not jdtls_execute_client_command_patched then
			jdtls_execute_client_command_patched = true
			local handler = vim.lsp.handlers["workspace/executeClientCommand"]
			vim.lsp.handlers["workspace/executeClientCommand"] = function(err, params, ctx)
				local result, resp_err = handler(err, params, ctx)
				if result == nil and resp_err == nil then
					result = vim.NIL
				end
				return result, resp_err
			end
		end
	end,
})

vim.lsp.enable("jdtls")
