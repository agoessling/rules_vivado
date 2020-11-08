`default_nettype none

module strobe_div #(
    parameter DIV = 10
) (
    input wire logic i_clk,
    input wire logic i_reset,
    output logic o_strobe
);

  // Bounds check DIV.
  if (DIV < 2) begin : param_check
    $error("DIV < 2: %d", DIV);
  end

  // Calculate size of counter based on divider.
  localparam WIDTH = $clog2(DIV);
  logic [WIDTH - 1:0] counter;
  initial counter = 0;

  always_ff @(posedge i_clk) begin
    if (counter == WIDTH'(DIV - 1) || i_reset) begin
      counter <= 0;
    end else begin
      counter <= counter + 1;
    end
  end

  assign o_strobe = counter == WIDTH'(DIV - 1);

`ifdef STROBE_DIV
  `define ASSUME assume
  `define COVER cover
`else
  `define ASSUME assert
  `define COVER(args) /*cover(args)*/
`endif

`ifdef FORMAL
  // Create flag for t<0.
  logic f_past_valid;
  initial f_past_valid = 0;
  always_ff @(posedge i_clk)
    f_past_valid <= 1;

  // Ensure strobe is set when counter is at maximum.
  always_comb
    if (counter == WIDTH'(DIV - 1))
      assert(o_strobe == 1);
    else
      assert(o_strobe == 0);

  // Ensure counter is always incrementing and resets correctly.
  always_ff @(posedge i_clk)
    if (!f_past_valid);
    else if ($past(counter) == WIDTH'(DIV - 1) || $past(i_reset))
      assert(counter == 0);
    else
      assert(counter == $past(counter) + 1);

  // Cover strobe working.
  always_ff @(posedge i_clk)
    `COVER(o_strobe == 1);
`endif
endmodule
