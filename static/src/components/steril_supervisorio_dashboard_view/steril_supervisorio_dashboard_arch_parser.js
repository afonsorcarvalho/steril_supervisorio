/** @odoo-module */

import { XMLParser } from "@web/core/utils/xml";

export class DashboardArchParser extends XMLParser {
    parse(arch) {
        const xmlDoc = this.parseXML(arch);
        const fieldFromTheArch = xmlDoc.getAttribute("fieldFromTheArch");
        return {
            fieldFromTheArch,
        };
    }
}