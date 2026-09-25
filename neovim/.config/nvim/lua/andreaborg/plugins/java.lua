return {
	{
		"JavaHello/spring-boot.nvim",
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			"mfussenegger/nvim-jdtls",
		},
		opts = {},
		config = function(_, opts)
			-- Disable embedded MCP server that spams "LSP[spring-boot][Info] Embedded Spring Tools MCP server started at port: 51490" + Press ENTER
			local launch = require("spring_boot.launch")
			local orig = launch.bootls_cmd
			launch.bootls_cmd = function(cfg)
				local cmd = orig(cfg)
				local has = false
				for _, v in ipairs(cmd) do
					if v:find("spring%.ai%.mcp%.server%.enabled", 1, true) then
						has = true
						break
					end
				end
				if not has then
					table.insert(cmd, 2, "-Dspring.ai.mcp.server.enabled=false")
				end
				return cmd
			end
			require("spring_boot").setup(opts)
		end,
	},
	{
		"mfussenegger/nvim-jdtls",
		ft = "java",
	},
}
