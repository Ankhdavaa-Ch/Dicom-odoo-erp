/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const WEEKDAYS = ["Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан", "Бямба", "Ням"];

export class HdcMyAttendance extends Component {
    static template = "hdc_employee_service.MyAttendance";

    setup() {
        this.orm = useService("orm");
        const now = new Date();
        this.state = useState({
            year: now.getFullYear(),
            month: now.getMonth(),
            loading: true,
            data: null,
            weeks: [],
        });
        onWillStart(() => this.load());
    }

    get monthTitle() {
        return `${this.state.year} оны ${this.state.month + 1} сар`;
    }

    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    }

    async load() {
        this.state.loading = true;
        const start = new Date(this.state.year, this.state.month, 1);
        const end = new Date(this.state.year, this.state.month + 1, 0);
        this.state.data = await this.orm.call(
            "hdc.attendance.daily",
            "get_my_attendance_dashboard",
            [this.formatDate(start), this.formatDate(end)]
        );
        this.buildWeeks();
        this.state.loading = false;
    }

    buildWeeks() {
        const map = new Map(this.state.data.days.map((d) => [d.date, d]));
        const first = new Date(this.state.year, this.state.month, 1);
        const last = new Date(this.state.year, this.state.month + 1, 0);
        const mondayOffset = (first.getDay() + 6) % 7;
        const gridStart = new Date(first);
        gridStart.setDate(first.getDate() - mondayOffset);
        const weeks = [];
        let cursor = new Date(gridStart);
        while (cursor <= last || weeks.length === 0 || weeks[weeks.length - 1].length < 7) {
            const week = [];
            for (let i = 0; i < 7; i++) {
                const key = this.formatDate(cursor);
                const source = map.get(key);
                week.push(source ? {...source, outside: false} : {
                    date: key, day: cursor.getDate(), weekday: i, outside: true,
                    is_weekend: i >= 5, planned: "", check_in: "", check_out: "", status: "outside",
                    worked: "00:00", late: "00:00", early: "00:00", overtime: "00:00",
                });
                cursor.setDate(cursor.getDate() + 1);
            }
            weeks.push(week);
            if (cursor > last && cursor.getDay() === 1) break;
        }
        this.state.weeks = weeks;
    }

    async previousMonth() {
        if (this.state.month === 0) { this.state.month = 11; this.state.year--; }
        else this.state.month--;
        await this.load();
    }

    async nextMonth() {
        if (this.state.month === 11) { this.state.month = 0; this.state.year++; }
        else this.state.month++;
        await this.load();
    }

    async today() {
        const now = new Date();
        this.state.year = now.getFullYear();
        this.state.month = now.getMonth();
        await this.load();
    }

    statusLabel(status) {
        return {
            present: "Ажилласан", late: "Хоцорсон", early_leave: "Эрт явсан",
            late_early: "Хоцорсон / Эрт явсан", overtime: "Илүү ажилласан",
            incomplete: "Гаралт бүртгэгдээгүй", absent: "Тасалсан", empty: "",
        }[status] || "";
    }
}

HdcMyAttendance.weekdays = WEEKDAYS;
registry.category("actions").add("hdc_employee_service.my_attendance", HdcMyAttendance);
