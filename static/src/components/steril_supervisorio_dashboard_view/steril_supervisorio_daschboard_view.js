/** @odoo-module */

import { registry } from "@web/core/registry";
import { DashboardController } from "./steril_supervisorio_dashboard_controller";
import { DashboardArchParser } from "./steril_supervisorio_dashboard_arch_parser";
import { DashboardModel } from "./steril_supervisorio_daschboard_model";
import { DashboardRenderer } from "./steril_supervisorio_dashboard_renderer";

export const DashboardView = {
    type: "ssdashboard",
    display_name: "Dashboard",
    icon: "fa fa-picture-o", // the icon that will be displayed in the Layout panel
    multiRecord: true,
    Controller: DashboardController,
    ArchParser: DashboardArchParser,
    Model: DashboardModel,
    Renderer: DashboardRenderer,

    props(genericProps, view) {
        const { ArchParser } = view;
        const { arch } = genericProps;
        const archInfo = new ArchParser().parse(arch);
        console.log(view)

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("ssDashboardView", DashboardView);