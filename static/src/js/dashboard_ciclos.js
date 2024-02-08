/** @odoo-module **/

import { registry } from '@web/core/registry';
//import { ListController } from "@web/views/list/list_controller"
import { KpiCard } from "../components/kpi_card/kpi_card"
import { ChartRenderer } from "../components/chart_renderer/chart_renderer"
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Layout } from "@web/search/layout";
const {  Component , useState,onWillStart,useSubEnv } = owl;

const states = [
    'iniciado',
    'em_andamento',
    'finalizado',
    'incompleto',
    'esperando_biologico',
    'esperando_aprovacao_supervisor',
    'abortado',
    'concluido',
    'cancelado',
    'reprovado',
]
export class DashboardCiclos extends Component {

    setup() {
        this.controlPanelDisplay = {};
        this.env.config.viewSwitcherEntries = [];
        this.context = useState(this.props.action.context);
        useSetupAction();
        useSubEnv({
            //ControlPanel trick : Allow the use of ControlPanel's bottom-right while disabling search to avoid errors
            searchModel:{
                searchMenuTypes : [],
            },
        });
        this.env.config.viewSwitcherEntries = [];

        this.state = useState({
            ciclos: {
                iniciado: {

                value: 0,
                percentage: 0
                },
                em_andamento: {

                value: 10,
                percentage: 0
                },
                finalizado: {

                value: 10,
                percentage: 0
                },
                incompleto: {

                value: 10,
                percentage: 0
                },
                esperando_biologico: {

                value: 10,
                percentage: 0
                },
                esperando_aprovacao_supervisor: {

                value: 10,
                percentage: 0
                },
                abortado: {

                value: 10,
                percentage: 0
                },
                concluido: {

                value: 10,
                percentage: 0
                },
                cancelado: {

                value: 10,
                percentage: 0
                },
                reprovado: {

                value: 10,
                percentage: 0
                },
            }
            ,
            period: 30,
        })
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.model = "steril_supervisorio.ciclos"
        onWillStart(async () => {
            this.getDates()
            await this.getData()
        })
    }
    async onChangePeriod(){
        this.getDates()
        await this.getData()
    }



    getDates(){
        this.state.current_date = moment().subtract(this.state.period, 'days').format('MM-DD-YYYY HH:mm:ss')
        console.log(this.state.current_date)
        this.state.previous_date = moment().subtract(this.state.period * 2, 'days').format('MM-DD-YYYY HH:mm:ss')
    }

    async getData(){
        let model = this.model
        let domain = [['state', 'in', ['finalizado']]]
       
        for (const e of states) {
            console.log( e)
            console.log(  this.state.ciclos)
            domain = [['state', 'in', [e]]]
            if (this.state.period > 0){
                domain.push(['data_inicio','>', this.state.current_date])
            }
            let count = await this.orm.searchCount(model, domain)
            if (count >= 0) {
                
                this.state.ciclos[e].value = count
            } else {
                this.state.ciclos[e].value = 0
            }
            console.log( this.state.ciclos[e])
            let prev_domain = [['state', 'in', [e]]]
            if (this.state.period > 0){
                prev_domain.push(['data_inicio','>', this.state.previous_date], ['data_inicio','<=', this.state.current_date])
            }
            const rawPrev_data = await this.orm.searchCount(model, prev_domain)
            var rawPercentage = ((count - rawPrev_data) / rawPrev_data) * 100
            rawPercentage = isNaN(rawPercentage) ? 0 : rawPercentage;
            const percentage = Math.min(100, Math.max(0, rawPercentage));
            this.state.ciclos[e].percentage = percentage.toFixed(2)
        }
        

        // previous period
    }
    async getCount(domain) {
        const count = await this.orm.searchCount(model, domain)
        return count
    }

    async goActionCiclos(value,name) {
       
        let domain = [['state', 'in', [value]]]
        let model = "steril_supervisorio.ciclos"
        if (this.state.period > 0){
            domain.push(['data_inicio','>', this.state.current_date])
        }
        console.log(this.actionService)
        //this.actionService.doAction("steril_supervisorio.ciclos_action_window")
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: name,
                res_model: "steril_supervisorio.ciclos",
                domain,
               
                context: {
                    create: false,
                },
                views: [
                    [false, "list"],[false, "form"]
                    
                ]
            }
        )

        
    }
    async goActionCiclosAndamento() {
        this.goActionCiclos('em_andamento',"Em Andamento")
    }
    async goActionCiclosIncompleto() {
        this.goActionCiclos('incompleto',"Incompletos")
    }
    async goActionCiclosFinalizados() {
        this.goActionCiclos('finalizado',"Finalizados")
    }
    async goActionCiclosConcluidos() {
        this.goActionCiclos('concluido',"Concluídos")
    }
    async goActionCiclosEsperandoResultados() {
        this.goActionCiclos('esperando_biologico', "Esperando Resultados")
    }
    async goActionCiclosReprovado() {
        this.goActionCiclos('reprovado', "Reprovados")
    }

}
DashboardCiclos.template = 'steril_supervisorio.DashboardCiclos'
DashboardCiclos.components = { KpiCard, ChartRenderer, ControlPanel,Layout }
registry.category('actions').add('steril_supervisorio.action_dashboard_ciclos', DashboardCiclos);