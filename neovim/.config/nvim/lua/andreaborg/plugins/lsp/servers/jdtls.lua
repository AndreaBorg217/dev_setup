return {
	before_init = function(_, config)
		local mason_packages = vim.fn.stdpath("data") .. "/mason/packages"
		local bundles = vim.split(
			vim.fn.glob(mason_packages .. "/java-debug-adapter/extension/server/com.microsoft.java.debug.plugin-*.jar"),
			"\n",
			{ trimempty = true }
		)
		local java_test_bundles =
			vim.split(vim.fn.glob(mason_packages .. "/java-test/extension/server/*.jar"), "\n", { trimempty = true })
		local excluded_java_test_bundles = {
			"com.microsoft.java.test.runner-jar-with-dependencies.jar",
			"jacocoagent.jar",
			"org.objectweb.asm_9.10.1.jar",
			"org.objectweb.asm.commons_9.10.1.jar",
			"org.objectweb.asm.tree_9.10.1.jar",
		}
		for _, java_test_bundle in ipairs(java_test_bundles) do
			local file_name = vim.fn.fnamemodify(java_test_bundle, ":t")
			if not vim.tbl_contains(excluded_java_test_bundles, file_name) then
				table.insert(bundles, java_test_bundle)
			end
		end
		vim.list_extend(bundles, require("spring_boot").java_extensions())
		config.init_options.bundles = bundles
	end,
	settings = {
		java = {
			completion = {
				importOrder = { "java", "javax", "org", "com" },
			},
			format = {
				enabled = false,
			},
			saveActions = {
				organizeImports = true,
			},
			sources = {
				organizeImports = {
					starThreshold = 999,
					staticStarThreshold = 999,
				},
			},
		},
	},
	on_attach = function()
		local jdtls = require("jdtls")
		jdtls.setup_dap({ hotcodereplace = "auto" })
		require("jdtls.dap").setup_dap_main_class_configs()
	end,
}
