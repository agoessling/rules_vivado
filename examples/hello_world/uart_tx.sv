`default_nettype none

module uart_tx #(
    parameter BAUD_DIV = 3,
    parameter DATA_BITS = 8
) (
    input wire logic i_clk,
    input wire logic i_reset,
    input wire logic [DATA_BITS - 1:0] i_data,
    input wire logic i_start,
    output logic o_busy,
    output logic o_tx
);

  logic baud_strobe;
  logic strobe_reset;
  strobe_div #(.DIV(BAUD_DIV)) strobe_div (
      .i_clk,
      .i_reset(strobe_reset),
      .o_strobe(baud_strobe)
  );

  localparam BITS = DATA_BITS + 2;
  logic [BITS - 2:0] shift_reg;  // One start and stop bit is naturally shifted in.
  initial shift_reg = 'b1;

  localparam IDLE = 0;
  localparam START_BIT = 1;
  localparam STOP_BIT = BITS;
  logic [$clog2(BITS + 1) - 1:0] state;  // One more state than bits.

  always_ff @(posedge i_clk) begin
    if (i_reset) begin
      state <= IDLE;
    end else if (state == IDLE && i_start) begin
      state <= START_BIT;
      shift_reg <= {i_data, 1'b0};
    end else if (baud_strobe) begin
      shift_reg <= {1'b1, shift_reg[BITS - 2: 1]};

      if (state == STOP_BIT) begin
        state <= IDLE;
      end else begin
        state <= state + 1;
      end
    end
  end

  always_comb begin
    strobe_reset = state == IDLE || i_reset;
    o_busy = state != IDLE;

    o_tx = shift_reg[0];
    if (state == IDLE) begin
      o_tx = 1'b1;
    end
  end

  initial begin
    state = IDLE;
  end

`ifdef FORMAL

`ifdef UART_TX
  `define ASSUME assume
  `define COVER cover
`else
  `define ASSUME assert
  `define COVER(args) /*cover(args)*/
`endif

  // Create flag for t<0.
  logic f_past_valid;
  initial f_past_valid = 0;
  always_ff @(posedge i_clk) begin
    f_past_valid <= 1;
  end

  localparam F_SEND_CYCLES = BAUD_DIV * (DATA_BITS + 2);
  logic [$clog2(F_SEND_CYCLES + 1) - 1:0] f_clk_counter;
  initial f_clk_counter = 0;
  logic [DATA_BITS + 1:0] f_data;
  initial f_data = 0;

  always_ff @(posedge i_clk) begin
    if (i_reset) begin
      f_clk_counter <= 0;
    end else if (i_start && !o_busy) begin
      f_clk_counter <= 1;
      f_data <= {1'b1, i_data, 1'b0};
    end else if (f_clk_counter >= F_SEND_CYCLES) begin
      f_clk_counter <= 0;
    end else if (f_clk_counter > 0) begin
      f_clk_counter <= f_clk_counter + 1;
    end
  end

  always_comb begin
    assert(o_busy == (f_clk_counter != 0));

    if (f_clk_counter == 0) begin
      assert(o_tx == 1);
    end else begin
      assert(o_tx == f_data[(f_clk_counter - 1) / BAUD_DIV]);
    end
  end

  always_ff @(posedge i_clk) begin
    `COVER(f_past_valid && !o_busy && !$past(i_reset) && $past(f_clk_counter) == F_SEND_CYCLES);
  end

`endif
endmodule
