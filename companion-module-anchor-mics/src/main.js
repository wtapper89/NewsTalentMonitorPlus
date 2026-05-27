const {
	InstanceBase,
	InstanceStatus,
	Regex,
	combineRgb,
	runEntrypoint,
} = require('@companion-module/base')

class AnchorMicsInstance extends InstanceBase {
	constructor(internal) {
		super(internal)
		this.pollTimer = null
		this.cachedState = { mics: [], variables: {} }
	}

	async init(config) {
		this.config = config
		this.updateActions()
		this.updateFeedbacks()
		this.updateVariableDefinitions()
		await this.startPolling()
	}

	async destroy() {
		this.stopPolling()
	}

	async configUpdated(config) {
		this.config = config
		await this.startPolling()
	}

	getConfigFields() {
		return [
			{
				type: 'textinput',
				id: 'host',
				label: 'Dashboard Host',
				width: 6,
				default: '127.0.0.1',
			},
			{
				type: 'textinput',
				id: 'port',
				label: 'Dashboard Port',
				width: 3,
				default: '8010',
				regex: Regex.PORT,
			},
			{
				type: 'checkbox',
				id: 'secure',
				label: 'Use HTTPS',
				width: 3,
				default: false,
			},
			{
				type: 'number',
				id: 'pollIntervalMs',
				label: 'Poll Interval (ms)',
				width: 6,
				default: 2000,
				min: 1000,
				max: 15000,
			},
		]
	}

	updateActions() {
		this.setActionDefinitions({
			refresh_now: {
				name: 'Refresh now',
				options: [],
				callback: async () => {
					await this.fetchState()
				},
			},
		})
	}

	updateFeedbacks() {
		this.setFeedbackDefinitions({
			mic_low_battery: {
				name: 'Mic low battery',
				type: 'boolean',
				label: 'Mic low battery',
				defaultStyle: {
					bgcolor: combineRgb(255, 191, 87),
					color: combineRgb(8, 17, 26),
				},
				options: [
					{
						id: 'micIndex',
						type: 'number',
						label: 'Mic index',
						default: 1,
						min: 1,
						max: 64,
					},
					{
						id: 'threshold',
						type: 'number',
						label: 'Battery threshold',
						default: 25,
						min: 1,
						max: 100,
					},
				],
				callback: (feedback) => {
					const mic = this.cachedState.mics[Number(feedback.options.micIndex) - 1]
					if (!mic) return false
					return Number(mic.battery_percent) <= Number(feedback.options.threshold)
				},
			},
			mic_has_error: {
				name: 'Mic has error',
				type: 'boolean',
				label: 'Mic has error',
				defaultStyle: {
					bgcolor: combineRgb(255, 107, 107),
					color: combineRgb(255, 255, 255),
				},
				options: [
					{
						id: 'micIndex',
						type: 'number',
						label: 'Mic index',
						default: 1,
						min: 1,
						max: 64,
					},
				],
				callback: (feedback) => {
					const mic = this.cachedState.mics[Number(feedback.options.micIndex) - 1]
					if (!mic) return false
					return !mic.is_online || (mic.errors && mic.errors.length > 0)
				},
			},
		})
	}

	updateVariableDefinitions() {
		const definitions = [
			{ variableId: 'summary_total', name: 'Summary: total microphones' },
			{ variableId: 'summary_assigned', name: 'Summary: assigned microphones' },
			{ variableId: 'summary_offline', name: 'Summary: offline microphones' },
			{ variableId: 'summary_low_battery', name: 'Summary: low-battery microphones' },
			{ variableId: 'summary_with_errors', name: 'Summary: microphones with errors' },
			{ variableId: 'summary_connection_status', name: 'Summary: backend connection status' },
			{ variableId: 'summary_updated_at', name: 'Summary: last update timestamp' },
		]

		this.cachedState.mics.forEach((mic, index) => {
			const prefix = `mic_${index + 1}`
			definitions.push({ variableId: `${prefix}_id`, name: `Mic ${index + 1}: id` })
			definitions.push({ variableId: `${prefix}_name`, name: `Mic ${index + 1}: name` })
			definitions.push({ variableId: `${prefix}_assignee`, name: `Mic ${index + 1}: assignee` })
			definitions.push({ variableId: `${prefix}_battery`, name: `Mic ${index + 1}: battery` })
			definitions.push({ variableId: `${prefix}_signal`, name: `Mic ${index + 1}: signal` })
			definitions.push({ variableId: `${prefix}_audio`, name: `Mic ${index + 1}: audio` })
			definitions.push({ variableId: `${prefix}_status`, name: `Mic ${index + 1}: status` })
			definitions.push({ variableId: `${prefix}_errors`, name: `Mic ${index + 1}: errors` })
			definitions.push({ variableId: `${prefix}_receiver`, name: `Mic ${index + 1}: receiver` })
			definitions.push({ variableId: `${prefix}_channel`, name: `Mic ${index + 1}: channel` })
		})

		this.setVariableDefinitions(definitions)
	}

	stopPolling() {
		if (this.pollTimer) {
			clearInterval(this.pollTimer)
			this.pollTimer = null
		}
	}

	async startPolling() {
		this.stopPolling()
		await this.fetchState()
		this.pollTimer = setInterval(() => {
			this.fetchState().catch((error) => {
				this.log('error', error.message)
			})
		}, Number(this.config.pollIntervalMs) || 2000)
	}

	getBaseUrl() {
		const protocol = this.config.secure ? 'https' : 'http'
		return `${protocol}://${this.config.host}:${this.config.port}`
	}

	async fetchState() {
		try {
			const response = await fetch(`${this.getBaseUrl()}/api/companion/state`)
			if (!response.ok) {
				throw new Error(`Backend request failed with ${response.status}`)
			}

			this.cachedState = await response.json()
			this.updateVariableDefinitions()
			this.setVariableValues(this.cachedState.variables || {})
			this.checkFeedbacks()
			this.updateStatus(InstanceStatus.Ok)
		} catch (error) {
			this.updateStatus(InstanceStatus.ConnectionFailure, error.message)
			throw error
		}
	}
}

runEntrypoint(AnchorMicsInstance, [])

