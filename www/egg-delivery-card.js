class EggDeliveryCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Please define an entity (next delivery sensor).");
    this.config = config;
  }
  set hass(hass) {
    this._hass = hass;
    this.render();
  }
  render() {
    if (!this._hass || !this.config) return;
    const entity = this._hass.states[this.config.entity];
    const dateText = entity?.state && entity.state !== "unknown" ? entity.state : "Not scheduled";
    const attrs = entity?.attributes || {};
    const nextDate = entity?.state && entity.state !== "unknown" ? new Date(`${entity.state}T00:00:00`) : null;
    const days = nextDate ? Math.ceil((nextDate - new Date(new Date().toDateString())) / 86400000) : "—";
    this.innerHTML = `
      <ha-card header="🥚 Egg Deliveries">
        <div style="padding:16px">
          <div style="font-size:12px;color:var(--secondary-text-color)">NEXT DELIVERY</div>
          <div style="font-size:24px;font-weight:600;margin:6px 0">${dateText}</div>
          <div style="font-size:28px;color:var(--success-color,var(--primary-color));font-weight:600">${days} days</div>
          <div style="color:var(--secondary-text-color);margin:4px 0 16px">${attrs.description || attrs.kind || "Upcoming delivery"}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <mwc-button id="log">Log delivery</mwc-button>
            <mwc-button id="special">Add special</mwc-button>
          </div>
        </div>
      </ha-card>`;
    this.querySelector("#log").addEventListener("click", () => this._hass.callService("egg_delivery_tracker", "log_delivery", {}));
    this.querySelector("#special").addEventListener("click", () => {
      const date = prompt("Special delivery date (YYYY-MM-DD)");
      if (!date) return;
      const description = prompt("Description", "Special delivery") || "Special delivery";
      const kind = confirm("Is this replacing the next regular delivery? OK = replacement, Cancel = additional") ? "replacement" : "additional";
      this._hass.callService("egg_delivery_tracker", "add_special_delivery", {date, description, kind});
    });
  }
  getCardSize() { return 3; }
}
customElements.define("egg-delivery-card", EggDeliveryCard);
window.customCards = window.customCards || [];
window.customCards.push({type: "egg-delivery-card", name: "Egg Delivery Tracker", description: "Egg delivery countdown and quick actions"});
