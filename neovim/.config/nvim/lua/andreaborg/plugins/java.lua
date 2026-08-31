return {
	{
		"JavaHello/spring-boot.nvim",
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			"mfussenegger/nvim-jdtls",
		},
		opts = {},
	},
	{
		"mfussenegger/nvim-jdtls",
		ft = "java",
	},
}
