## Clock.
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports {i_clk}];

## Outputs.
# UART TX.  This gives a 100ns allowed window centered on the clock edge.
set_output_delay -clock sys_clk_pin -min 50 [get_ports {o_tx}];  # Min is -t_h.
set_output_delay -clock sys_clk_pin -max -50 [get_ports {o_tx}];  # Max is t_su.
